# import base64
import json
import os
import sqlite3
from typing import Optional

from dotenv import load_dotenv
from google import genai
from PIL import Image
from langchain.agents import create_agent
from langchain.tools import tool
# from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from reviewsAPI import get_product_rating

load_dotenv()

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)




# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def search_products(query: str, max_price: Optional[float] = None, is_organic: Optional[bool] = None) -> str:
    """
    Search the product database by keyword (matched against name, description, and category).
    Optionally filter by maximum price and/or organic status.
    Returns a JSON array of matching products, each with: id, name, category, price,
    description, is_organic.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql = "SELECT id, name, category, price, description, is_organic FROM products WHERE 1=1"
    # WHERE 1=1 is a common SQL trick to simplify appending additional conditions. It always evaluates to true, so you can safely add AND clauses without worrying about whether it's the first condition or not.This is because
    # we can use AND only after a WHERE clause. If we didn't have WHERE 1=1, we'd have to check if it's the first condition and use WHERE instead of AND.
    params: list = []
    # This list stores values that replace ? later.
    if query:
        sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like])
        # suppose query is "honey", then like will be "%honey%". This means we are looking for any product whose name, description, or category contains the word "honey" anywhere in it. The % is a wildcard in SQL that matches any sequence of characters.
        # now params becomes ["%honey%", "%honey%", "%honey%"] which will be used to replace the ? in the SQL query.

    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)
      # suppose max_price is 20, then we are adding a condition that the price of the product should be less than or equal to 20. We append 20 to params, so now params becomes ["%honey%", "%honey%", "%honey%", 20].
    if is_organic is not None:
        sql += " AND is_organic = ?"
        params.append(1 if is_organic else 0)
      # suppose is_organic is True, then we are adding a condition that the product should be organic. We append 1 to params, so now params becomes ["%honey%", "%honey%", "%honey%", 20, 1]. If is_organic was False, we would append 0 instead.
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    # now current params is ["%honey%", "%honey%", "%honey%", 20, 1] and sql is "SELECT id, name, category, price, description, is_organic FROM products WHERE 1=1 AND (name LIKE ? OR description LIKE ? OR category LIKE ?) AND price <= ? AND is_organic = ?". So the actual query becomes
    # SELECT id, name, category, price, description, is_organic
    # FROM products
    # WHERE 1=1
    # AND (
    #     name LIKE '%honey%'
    #     OR description LIKE '%honey%'
    #     OR category LIKE '%honey%'
    # )
    # AND price <= 20
    # AND is_organic = 1
    # now the cursor will execute this query and fetch all the rows that match the conditions. Each row will be a tuple containing the values of id, name, category, price, description, and is_organic for a product.
    products = [
        {
            "id":          row[0],
            "name":        row[1],
            "category":    row[2],
            "price":       row[3],
            "description": row[4],
            "is_organic":  bool(row[5]),
        }
        for row in rows
    ]
    return json.dumps(products)
    # the list of product dictionaries is converted into a JSON string and returned. Each product dictionary has keys "id", "name", "category", "price", "description", and "is_organic" with their corresponding values from the database.
    # JSON string looks like a dictionary but is actually a string.We need to
    # convert it to a string because the tool interface expects a string return value.Also tools,API nad LLMs often coomunicate using text formats like JSON, so it's common to return data as a JSON string.

@tool
def get_rating(product_id: int) -> str:
    """
    Get the average customer rating and total review count for a product by its ID.
    Returns a JSON object with: product_id, average_rating, review_count.
    """
    result = get_product_rating(product_id)
    return json.dumps(result)


@tool
def checkout(product_id: int) -> str:
    """
    Place an order for the given product ID. Saves the order to the database and returns
    a confirmation message with the order ID, product name, and price.
    """
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return f"Error: product with ID {product_id} not found."

    name, price = row
    # unpack the row tuple into name and price variables. row[0] is the product name and row[1] is the product price. This makes it easier to use these values in the next steps.
    cursor.execute(
        "INSERT INTO orders (product_id, product_name, price) VALUES (?, ?, ?)",
        (product_id, name, price),
    )
    # now we are inserting a new order into the orders table. The values for product_id, product_name, and price are provided as a tuple (product_id, name, price). This will create a new record in the orders table with the specified product details.
    order_id = cursor.lastrowid
    # After insertion SQLite automatically creates an order id.
    conn.commit()
    # This is important because without committing, the new order would not be saved and would be lost when the connection is closed.
    conn.close()

    return (
        f"Order #{order_id} confirmed! '{name}' has been successfully ordered for ${price:.2f}. "
        f"Your order will arrive in 3-5 business days. Thank you for shopping with us!"
        # :.2f shows 2 digits after decimal.
    )


@tool
def describe_product_image(image_path: str) -> str:
    """
    Analyze a product image and return its key attributes as a JSON object.
    Use this when the user uploads a photo of a product they are interested in.
    The returned attributes can be used directly with search_products.
    """
    # with open(image_path, "rb") as f:
    #     image_data = base64.b64encode(f.read()).decode()

    # ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    # # suppose image_path is "honey.jpg", then os.path.splitext(image_path) returns ("honey", ".jpg"). We take the second element (the extension), convert it to lowercase, and remove the leading dot. So ext becomes "jpg".
    # mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    # # mime type is used to tell the browser or any other software what kind of file it is. For jpg and jpeg files, we use "image/jpeg". For other extensions, we use "image/<ext>", where <ext> is the actual extension (like png, gif, etc.).
    # message = HumanMessage(content=[
    #     {
    #         "type": "image_url",
    #         "image_url": {"url": f"data:{mime};base64,{image_data}"},
    #     },
    #     {
    #         "type": "text",
    #         "text": (
    #             "Look at this product image and extract its key attributes. "
    #             "Return ONLY a JSON object with these fields:\n"
    #             "- product_type: what kind of product it is (e.g. honey, olive oil, almonds)\n"
    #             "- search_query: a short keyword to search for it (e.g. 'honey', 'olive oil')\n"
    #             "- is_organic: true if the label says organic, false if not, null if unclear\n"
    #             "- description: one sentence describing the product"
    #         ),
    #     },
    # ])
    # # the human message consists of the image and text instructions. The image is provided as a data URL with the appropriate MIME type and base64-encoded image data. The text instructs the model to analyze the image and return a JSON object with specific fields describing the product.

    # response = vision_llm.invoke([message])
    # return response.content
    image = Image.open(image_path)

    prompt = """
Look at this product image.

Return ONLY this JSON:

{
  "product_type":"",
  "search_query":"",
  "is_organic": true,
  "description":""
}

Do not return markdown.
Return only JSON.
"""

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image]
    )

    return response.text


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

agent = create_agent(
    tools=[search_products, get_rating, checkout, describe_product_image],
    model=llm,
    system_prompt=(
        "You are a helpful shopping assistant. Follow these rules strictly.\n\n"
        "IMAGE SEARCH — when the user provides an image path:\n"
        "1. Call describe_product_image with the path to identify the product.\n"
        "2. Use the returned search_query and is_organic to call search_products.\n"
        "3. Continue with the BROWSING flow from step 2 onwards.\n\n"
        "BROWSING — when the user describes what they want to buy:\n"
        "1. Call search_products to find matching items (apply any price/organic filters given).\n"
        "2. For each candidate, call get_rating to retrieve its average rating.\n"
        "3. Filter by the user's minimum rating if specified.\n"
        "4. Present qualifying products as a numbered list. For each item use this exact format "
        "   (plain text, no backticks, no code blocks, no bold, no italic):\n\n"
        "   #<number>. <name> (ID:<product_id>) — $<price> ★<rating> — <organic or non-organic>\n\n"
        "   Add a blank line between each product entry for readability. "
        "   Always include (ID:X) so you can reference it later.\n"
        "5. If only one product qualifies, still show it in the list and ask: "
        "   'Would you like to order it? Just say yes or give me the number.'\n"
        "6. Do NOT call checkout at this stage.\n\n"
        "ORDERING — when the user confirms they want to buy (e.g. 'yes', 'sure', 'go ahead', "
        "'order number 2', 'the first one', 'get me #3'):\n"
        "1. Look at your previous message to find the (ID:X) for the chosen product "
        "   (if only one was listed and the user says 'yes', use that product's ID).\n"
        "2. Call checkout with that product_id (the number from (ID:X)).\n"
        "3. Confirm the order to the user in plain text.\n\n"
        "Never place an order unless the user explicitly confirms. "
        "Never guess a product_id — always take it from the (ID:X) in your own previous message."
    ),
)

if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "I want to buy organic honey with 4.5+ rating and less than $20 price."
                    ),
                }
            ]
        }
    )
    print(result["messages"][-1].content)