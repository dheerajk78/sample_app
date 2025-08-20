from flask import Flask, Response
from tracker import get_portfolio_summary
 
app = Flask(__name__)
 
@app.route("/")
def summary():
    try:
        # Adjust csv path if needed for cloud storage or mount points
        csv_path = "transactions.csv"
        summary_text = get_portfolio_summary(csv_path)
        return Response(summary_text, mimetype="text/plain")
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)
