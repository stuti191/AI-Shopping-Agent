"""
Reviews API — reads from the `reviews` table in store.db and returns
aggregated rating information for products.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")
# os.path.dirname(__file__) returns the directory of the current file (reviewsAPI.py), and os.path.join combines it with "store.db" to get the full path to the database file. This ensures that the code can find store.db regardless of where it's run from, as long as store.db is in the same directory as reviewsAPI.py.


def get_product_rating(product_id: int) -> dict:
    """Return average rating and review count for a single product."""
    conn = sqlite3.connect(DB_PATH)
    # creates a connection to store.db
    cursor = conn.cursor()
    # A cursor is used to execute SQL queries.
    cursor.execute(
        "SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id = ?",
        (product_id,),
        # it is a parameterized query, where the ? is a placeholder for the product_id value. comma after product_id i.e (product_id,) is necessary to make it a tuple, which is required by the execute method for parameter substitution.
    )
    row = cursor.fetchone()
    # the result table from the query will have one row with two columns: the average rating and the count of reviews. fetchone() retrieves that single row as a tuple.
    conn.close()

    avg = round(row[0], 2) if row and row[0] is not None else 0.0
    # row is a tuple with 1st element as average rating and 2nd element as count. row[0] is the average rating. If row exists and row[0] is not None, it rounds the average rating to 2 decimal places. Otherwise, it defaults to 0.0.
    count = row[1] if row else 0
    return {"product_id": product_id, "average_rating": avg, "review_count": count}


def get_ratings_for_products(product_ids: list[int]) -> list[dict]:
    """Return ratings for a list of product IDs."""
    if not product_ids:
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(product_ids))
    # if suppose len(product_ids) is 4, placeholders will be '?,?,?,?'.This is
    # later used in WHERE product_id IN (?,?,?,?)
    cursor.execute(
        f"""
        SELECT product_id, AVG(rating), COUNT(*)
        FROM reviews
        WHERE product_id IN ({placeholders})
        GROUP BY product_id
        """,
        product_ids,
    )
    rows = cursor.fetchall()
    conn.close()

    ratings_map = {r[0]: {"average_rating": round(r[1], 2), "review_count": r[2]} for r in rows}
    return [
        {
            "product_id": pid,
            "average_rating": ratings_map.get(pid, {}).get("average_rating", 0.0),
            "review_count":   ratings_map.get(pid, {}).get("review_count", 0),
        }
        for pid in product_ids
    ]


if __name__ == "__main__":
    # Single product
    result = get_product_rating(1)
    print("Single product rating:")
    print(f"  Product {result['product_id']}: {result['average_rating']} stars ({result['review_count']} reviews)")

    # Multiple products
    print("\nBatch ratings:")
    results = get_ratings_for_products([1, 3, 5, 7])
    for r in results:
        print(f"  Product {r['product_id']}: {r['average_rating']} stars ({r['review_count']} reviews)")
