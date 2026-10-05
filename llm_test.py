import os
import pyodbc
from openai import OpenAI

# 1. Configuration
DSN_NAME = "localhost_live"
# Initialize OpenAI client (Ensure OPENAI_API_KEY is set in your environment variables)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_all_recent_order_history(limit_customers: int = 5) -> dict:
    """
    Fetches recent transaction histories across the entire database,
    grouping records by CustomerID to make the process completely customer-agnostic.
    """
    # Fetch orders from the most active or recent customers
    query = f"""
        WITH RecentCustomers AS (
            SELECT DISTINCT TOP ({limit_customers}) CustomerID 
            FROM [dbo].[order_history]
            ORDER BY CustomerID DESC
        )
        SELECT 
            CustomerID,
            CustomerName,
            ProductName,
            ProductCategory,
            EventDateTime,
            EventValue
        FROM 
            [dbo].[order_history]
        WHERE 
            CustomerID IN (SELECT CustomerID FROM RecentCustomers)
        ORDER BY 
            CustomerID, EventDateTime DESC;
    """
    
    conn_str = f"DSN={DSN_NAME};Trusted_Connection=yes;"
    grouped_history = {}
    
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    cust_id = row_dict['CustomerID']
                    
                    if cust_id not in grouped_history:
                        grouped_history[cust_id] = []
                    grouped_history[cust_id].append(row_dict)
                    
    except Exception as e:
        print(f"Database error: {e}")
        
    return grouped_history

def build_rag_prompt(customer_name: str, history: list) -> str:
    """Transforms an arbitrary customer's history into a structured prompt."""
    history_lines = []
    for item in history:
        date_str = item['EventDateTime'].strftime('%Y-%m-%d') if hasattr(item['EventDateTime'], 'strftime') else str(item['EventDateTime'])
        line = (
            f"- Purchased '{item['ProductName']}' (Category: {item['ProductCategory']}) "
            f"on {date_str} for ${item['EventValue']}"
        )
        history_lines.append(line)
        
    history_text = "\n".join(history_lines)
    
    prompt = f"""
You are an expert retail recommendation engine. Based on the customer's transaction history below, recommend 3 new products or categories they are likely to buy next. Provide a brief, persuasive reason for each recommendation.

Customer Name: {customer_name}

Purchase History:
{history_text}

Recommendations:
"""
    return prompt

def generate_recommendations(prompt: str) -> str:
    """Sends the context prompt to OpenAI."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful retail assistant generating personalized purchase recommendations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating recommendations from LLM: {e}"

# 2. Execution Pipeline
if __name__ == "__main__":
    print("Fetching global order history records from [dbo].[order_history]...")
    # Get transaction histories for the top 3 dynamic customers found in the DB
    all_customers_data = get_all_recent_order_history(limit_customers=3)
    
    if not all_customers_data:
        print("No order history records found in the database.")
    
    # Process whichever customers were returned by the query dynamically
    for customer_id, history in all_customers_data.items():
        print(f"\n{"="*50}")
        
        # Pull profile details safely from the payload
        first_record = history[0]
        customer_name = first_record.get('CustomerName') or f"Customer #{customer_id}"
        
        print(f"Processing completely dynamic data package for: {customer_name} (ID: {customer_id})")
        print(f"Items found in profile history: {len(history)}")
        
        # Build & stream to LLM
        rag_prompt = build_rag_prompt(customer_name, history)
        recommendations = generate_recommendations(rag_prompt)
        
        print(f"\n--- RECOMMENDATIONS FOR {customer_name.upper()} ---")
        print(recommendations)
