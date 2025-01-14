from  flask import Flask, render_template, request
import pickle
import pandas as pd
import os
#
from arize.pandas.logger import Client, Schema
from arizeutils.types import ModelTypes, Environments
#
from dotenv import load_dotenv
load_dotenv() 
import datetime

ARIZE_SPACE_KEY=os.getenv("SPACE_KEY")
ARIZE_API_KEY = os.getenv("API_KEY")

# Initialize Arize client with your space key and api key
arize_client = Client(space_key=ARIZE_SPACE_KEY, api_key=ARIZE_API_KEY)

# Define the schema for your data
schema = Schema(
    prediction_id_column_name="prediction_id",
    timestamp_column_name="timestamp",
    feature_column_names=["Credit_line_outstanding", "Loan_amt_outstanding", "Total_debt_outstanding", "Income", "Years_employed", "Fico_score"],
    prediction_label_column_name="prediction_label",
    actual_label_column_name="actual_label"
)


app = Flask(__name__)
model = pickle.load(open("catboost_model-2.pkl", "rb"))


def model_pred(features):
    test_data = pd.DataFrame([features])
    prediction = model.predict(test_data)
    return int(prediction[0])


@app.route("/", methods=["GET"])
def Home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    if request.method == "POST":
        Credit_line_outstanding = int(request.form["Credit_line_outstanding"])
        Loan_amt_outstanding = float(request.form["Loan_amt_outstanding"])
        Total_debt_outstanding = float(request.form["Total_debt_outstanding"])
        Income = float(request.form["Income"])
        Years_employed = int(request.form["Years_employed"])
        Fico_score = int(request.form["Fico_score"])

        # Assume you have actual labels available for evaluation
        actual_label = int(request.form.get("actual_label for evaluation", 1))  # Default to -1 if not provided
        #

        prediction = model.predict(
            [[Credit_line_outstanding, Loan_amt_outstanding, Total_debt_outstanding, Income, Years_employed, Fico_score]]
        )
        # Log the prediction to Arize
        timestamp = pd.Timestamp.now()

        # Log the prediction to Arize
        data = {
            "prediction_id": [str(timestamp.timestamp())],  # Unique ID for each prediction
            "timestamp": [timestamp],
            "Credit_line_outstanding": [Credit_line_outstanding],
            "Loan_amt_outstanding": [Loan_amt_outstanding],
            "Total_debt_outstanding": [Total_debt_outstanding],
            "Income": [Income],
            "Years_employed": [Years_employed],
            "Fico_score": [Fico_score],
            "prediction_label": [int(prediction[0])],
            "actual_label": [actual_label]             
        }
        dataframe = pd.DataFrame(data)
        
        try: 
            response = arize_client.log(
                dataframe = dataframe,
                model_id="Catboost_model",
                model_version="v1",
                model_type=ModelTypes.SCORE_CATEGORICAL,
                environment=Environments.PRODUCTION,
                #features=features,
                #prediction_label = [int(prediction[0])],
                schema=schema
            )

            if response.status_code != 200:
                print(f"Failed to log data to Arize: {response.text}")
            else:
                print("Successfully logged data to Arize")
        except Exception as e:
            print(f"An error occured: {e}")
        
        if prediction[0] == 1:
            return render_template(
                "index.html",
                prediction_text="Make an appointment with your banker",
            )

        else:
            return render_template(
                "index.html", prediction_text="You are in default of payment :)"
            )

    else:
        return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
