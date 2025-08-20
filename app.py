from flask import Flask, Response
from tracker import get_portfolio_summary
import os
# test
app = Flask(__name__)
print("‼ CMD is:", os.getenv("CMD_OVERRIDE", "gunicorn app:app"))
@app.route("/")
def summary():
    try:
        # Adjust csv path if needed for cloud storage or mount points
        csv_path = "transactions.csv"
        summary_text = get_portfolio_summary(csv_path)
        return Response(summary_text, mimetype="text/plain")
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
