from flask import (
    Flask,
    request,
    jsonify,
    Response,
    redirect,
    session,
    url_for,
    send_from_directory,
)
from flask_cors import CORS, cross_origin
from config import ApplicationConfig
from models import db

from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.chat_routes import chat_bp
from auth_middleware import token_required

from langchain import OpenAI, SQLDatabase

# from langchain_experimental.sql import SQLDatabaseChain
# from langchain_experimental.sql.base import SQLDatabaseSequentialChain
import os
import openai
import pinecone
import traceback

# import ast
import re
from pymongo import MongoClient
from datetime import date, datetime
from edi_835_parser import parse
from config import ApplicationConfig
from train import *

# Set Entire App
app = Flask(__name__)

# Configuration
app.config.from_object(ApplicationConfig)

OPENAI_KEY = app.config["OPENAI_KEY"]
MAILGUN_API_KEY = app.config["MAILGUN_API_KEY"]
MAILGUN_DOMAIN = app.config["MAILGUN_DOMAIN"]
GOOGLE_CLIENT_ID = app.config["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = app.config["GOOGLE_CLIENT_SECRET"]
PG_USER = app.config["PG_USER"]
PG_PASS = app.config["PG_PASS"]
PG_HOST = app.config["PG_HOST"]
PG_DB = app.config["PG_DB"]
SECRET_KEY = app.config["SECRET_KEY"]
UPLOAD_FOLDER = app.config["UPLOAD_FOLDER"]

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}/{PG_DB}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = SECRET_KEY
# Configuration end

# Set middleware

CORS(app, supports_credentials=True)

# Database Configuration
db.init_app(app)


# Create tables
@app.before_request
def create_tables():
    db.create_all()


# Route Configuration
@user_bp.before_request
@chat_bp.before_request
@token_required
def before_request():
    pass


app.register_blueprint(auth_bp, url_prefix="/v2/auth")
app.register_blueprint(user_bp, url_prefix="/v2/user")
app.register_blueprint(chat_bp, url_prefix="/v2/chat")


##########################################################################################
##########################################################################################
##########################################################################################
########################## Get response using given prompt ###############################
key = PINECONE_API_KEY
env_value = PINECONE_ENV

try:
    pinecone.init(api_key=key, environment=env_value)
    activate_indexs = pinecone.list_indexes()

    PINECONE_INDEX = pinecone.Index(activate_indexs[0])
    openai.api_key = OPENAI_KEY

except Exception as e:
    raise e


llm = OpenAI(openai_api_key=OPENAI_KEY, temperature=0.1)
current_path = os.path.dirname(__file__)

# dburi = os.path.join("sqlite:///" + current_path, "static", "database.db")
# dburi = 'sqlite:///E:/Divyang/gabeo-boc/backend/backend/gabeo_poc/static/database.db'


# database = SQLDatabase.from_uri(dburi)
# sequential_chain = SQLDatabaseSequentialChain.from_llm(
#     llm=llm, db=database, verbose=True, return_intermediate_steps=True
# )
# db_chain = SQLDatabaseChain(
#     llm=llm, database=database, verbose=True, return_intermediate_steps=True
# )

# mongodb = MongoClient("mongodb://localhost:27017")
# db = mongodb["gabeo"]
# claims = db["claims"]


# @app.route("/v2/icd/", methods=["POST", "GET"])
# def getIcd():
#     if request.method == "POST":
#         keyword = request.get_json()["keyword"]
#         try:
#             conn = sqlite3.connect("./static/database.db")
#             cursor = conn.cursor()
#             query = f"SELECT * FROM ICD10 WHERE WHO_Full_Desc LIKE '%{keyword}%' OR ICD10_Code LIKE '%{keyword}%' LIMIT 20"
#             cursor.execute(query)
#             rows = cursor.fetchall()
#             results = []

#             for row in rows:
#                 CODE = row[1]
#                 DESCRIPTION = row[2]
#                 results.append({"DESCRIPTION": DESCRIPTION, "CODE": CODE})
#             cursor.close()
#             conn.close()
#             return jsonify(results)
#         except Exception as e:
#             raise e
#     else:
#         return jsonify({"message": "Invalid request method"})


# @app.route("/v2/get_main/", methods=["POST", "GET"])
# def getMain():
#     if request.method == "POST":
#         keyword = request.get_json()["keyword"]
#         try:
#             conn = sqlite3.connect("./static/database.db")
#             conn.row_factory = (
#                 sqlite3.Row
#             )  # Set row factory to access rows by field name
#             cursor = conn.cursor()
#             # sql_query = f"""SELECT
#             #                 c.*,  -- Select all columns from the 'claims' table
#             #                 (
#             #                     SELECT GROUP_CONCAT(d.ICD10_Code)
#             #                     FROM Diagnosis d
#             #                     WHERE c.ClaimID = d.ClaimID
#             #                 ) AS Diagnosis_Codes,  -- Subquery to retrieve diagnosis codes as an array
#             #                 (
#             #                     SELECT GROUP_CONCAT(p.CPT_Code)
#             #                     FROM Procedures p
#             #                     WHERE c.ClaimID = p.ClaimID
#             #                 ) AS Procedure_Codes  -- Subquery to retrieve procedure codes as an array
#             #             FROM
#             #                 claims c
#             #             WHERE
#             #                 c.ClaimID LIKE ? OR c.ServiceProvider LIKE ? OR c.DeniedPayerName LIKE ? OR c.CARC LIKE ? OR c.RARC LIKE ? OR c.DeniedType LIKE ? OR c.DeniedDescription LIKE ? OR c.PatientID LIKE ?
#             #             LIMIT 10
#             #         """

#             sql_query = """
#                 SELECT
#                     c.*,  -- Select all columns from the 'claims' table
#                     (
#                         SELECT GROUP_CONCAT(d.ICD10_Code)
#                         FROM Diagnosis d
#                         WHERE c.ClaimID = d.ClaimID
#                     ) AS Diagnosis_Codes,  -- Subquery to retrieve diagnosis codes as an array
#                     (
#                         SELECT GROUP_CONCAT(p.CPT_Code)
#                         FROM Procedures p
#                         WHERE c.ClaimID = p.ClaimID
#                     ) AS Procedure_Codes,  -- Subquery to retrieve procedure codes as an array
#                     n.NPI,  -- Include NPI column from 'npidata' table
#                     n.ProviderFirstName,  -- Include ProviderFirstName column from 'npidata' table
#                     n.ProviderLastNameLegalName,
#                     n.ProviderMiddleName,
#                     n.ProviderFirstLineBusinessMailingAddress,
#                     n.NPI
#                 FROM
#                     claims c
#                 LEFT JOIN npidata n ON c.NPI = n.NPI
#                 WHERE
#                     c.ClaimID LIKE ? OR c.DeniedPayerName LIKE ? OR c.CARC LIKE ? OR c.RARC LIKE ? OR c.DeniedType LIKE ? OR c.DeniedDescription LIKE ? OR c.PatientID LIKE ?
#                 LIMIT 10
#                 """

#             cursor.execute(sql_query, (f"%{keyword}%",) * 7)
#             rows = cursor.fetchall()
#             results = []

#             for row in rows:
#                 results.append(
#                     {
#                         "ClaimID": row["ClaimID"],
#                         "NPI": row["NPI"],
#                         "DeniedPayerName": row["DeniedPayerName"],
#                         "DeniedCARC": row["CARC"],
#                         "DeniedRARC": row["RARC"],
#                         "DeniedType": row["DeniedType"],
#                         "DeniedDescription": row["DeniedDescription"],
#                         "PatientID": row["PatientID"],
#                         "ProcedureCodes": row["Procedure_Codes"],
#                         "DateOfService": row["DateOfService"],
#                         "ProviderFirstName": row["ProviderFirstName"],
#                         "ProviderLastName": row["ProviderLastNameLegalName"],
#                         "ProviderMiddleName": row["ProviderMiddleName"],
#                         "ProviderAddress": row[
#                             "ProviderFirstLineBusinessMailingAddress"
#                         ],
#                         "ProviderNPI": row["NPI"],
#                     }
#                 )
#             cursor.close()
#             conn.close()
#             return jsonify(results)
#         except Exception as e:
#             raise e
#     else:
#         return jsonify({"message": "Invalid request method"})


@app.route("/v2/upload_documents", methods=["POST", "GET"])
def upload_documents():
    if request.method == "POST":
        # Check if the POST request has a file part
        len = int(request.form["length"])
        namespace = request.form["namespace"]
        if len == 0:
            return "No file part"

        for i in range(len):
            document_file = request.files[f"file-{i}"]

            # Ensure the uploads folder exists, create it if necessary
            if not os.path.exists(app.config["UPLOAD_FOLDER"]):
                os.makedirs(app.config["UPLOAD_FOLDER"])

            # Save the uploaded PDF file to the uploads folder
            document_file.save(
                os.path.join(app.config["UPLOAD_FOLDER"], document_file.filename)
            )

            # Optionally, you can perform further processing on the uploaded PDF file here

        status = train_documents(app.config["UPLOAD_FOLDER"], namespace)
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ TRAIN STATUS", status)
        if status == True:
            return {"status": "success"}
        else:
            return {"status": "failed"}


# @app.route("/v2/query_csv/", methods=["POST", "GET"])
# def csv_query():
#     if request.method == "POST":
#         query = request.form["query"]
#         try:
#             # res = db_chain(query)
#             res = sequential_chain(query)
#             steps = res["intermediate_steps"]
#             text = steps[0]["input"]
#             summary = res["result"]

#             ########### Get Headers ###################
#             split_text = text.split("SELECT")[1].split("FROM")[0].strip()

#             # Split the header names based on commas and remove any surrounding quotes or spaces
#             header_names = [name.strip('"') for name in split_text.split(",")]

#             ########### Get Values #####################
#             result_match = re.search(r"SQLResult: (.+)", text)
#             if result_match:
#                 sql_result = result_match.group(1)
#                 array_sql_result = ast.literal_eval(sql_result)
#                 # message = get_medical_necessity(query)
#                 # print(message)
#                 # message = chatPDF()
#                 return jsonify(
#                     {
#                         "headers": header_names,
#                         "table": array_sql_result,
#                         "summary": summary,
#                         "pdfContent": 'message["content"]',
#                         "type": "details",
#                     }
#                 )
#             else:
#                 return {"message": "no match"}
#         except Exception as e:
#             raise e


# @app.route("/v2/query_main/", methods=["POST", "GET"])
# def main_query():
#     if request.method == "POST":
#         query = request.form["query"]
#         try:
#             # res = db_chain(query)
#             res = sequential_chain(query)
#             print(res)
#             steps = res["intermediate_steps"]
#             text = steps[0]["input"]
#             summary = res["result"]

#             ########### Get Headers ###################
#             split_text = text.split("SELECT")[1].split("FROM")[0].strip()

#             # Split the header names based on commas and remove any surrounding quotes or spaces
#             header_names = [name.strip('"') for name in split_text.split(",")]

#             ########### Get Values #####################
#             result_match = re.search(r"SQLResult: (.+)", text)
#             if result_match:
#                 sql_result = result_match.group(1)
#                 array_sql_result = ast.literal_eval(sql_result)
#                 # message = get_medical_necessity(query)
#                 # print(message)
#                 # message = chatPDF()
#                 return jsonify(
#                     {
#                         "headers": header_names,
#                         "table": array_sql_result,
#                         "summary": summary,
#                         "type": "details",
#                     }
#                 )
#             else:
#                 return {"summary": "no match"}
#         except Exception as e:
#             print(str(e))
#             return {"summary": "Can't understand what you mean."}


# def get_claim_details(query, claim_number):
#     prompt = f"""
#         Find all the records such as diagnosis code and description, CPT codes and description, Patientid, payer, DenialReasonCode and Description, everything related to this claim {claim_number}.
#         If there is not any relation between above information and inputted claim nuber, you don't need to generate it.
#     """
#     res = sequential_chain(prompt)
#     steps = res["intermediate_steps"]
#     sql_result = steps[3]


# def getSpecific(query, claim_number):
#     try:
#         res = getClaimDetails(claim_number)

#         assistant = str(res["content"][0])

#         res = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             temperature=0.1,
#             stop=None,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You are medical chatbot. You are the first AI-driven platform that fully automates the denial management process. You will be given specific denial data from the use and you need to give back detailed instruction about the user query based on the given specific data.",
#                 },
#                 {"role": "user", "content": assistant},
#                 {"role": "user", "content": query},
#             ],
#         )
#         # message = res.choices[0].text
#         message = res["choices"][0]["message"]["content"]

#         return {"content": message, "type": "generic"}
#     except Exception as e:
#         raise e


# def getClaimDetails(claim_number):
#     try:
#         conn = sqlite3.connect("./static/database.db")
#         cursor = conn.cursor()
#         query = f"SELECT * FROM MainData WHERE ClaimNumber LIKE '%{claim_number}%'"
#         cursor.execute(query)
#         rows = cursor.fetchall()
#         results = []
#         for row in rows:
#             results.append(
#                 {
#                     "DOS": row[0],
#                     "Claim Number": row[10],
#                     "CPT": row[23],
#                     "Provider": row[34],
#                     "Payer": row[6],
#                     "Sec Payer": row[8],
#                     "DX1_Codes": row[28],
#                     "DX2_Codes": row[29],
#                     "DX3_Codes": row[30],
#                     "DX4_Codes": row[31],
#                     "Mod1": row[24],
#                     "Mod2": row[25],
#                     "Mod3": row[26],
#                     "Mod4": row[27],
#                     "Charge": row[12],
#                     "Allowed": row[14],
#                     "Paid": row[13],
#                     "Adjusted": row[15],
#                     "Refund": row[16],
#                     "Balance": row[22],
#                     "FirstDeniedReasonCode": row[42],
#                     "FirstDeniedType": row[43],
#                     "FirstDeniedReasonDescription": row[44],
#                     "FirstDeniedDate": row[37],
#                     "FirstDeniedAmount": row[38],
#                     "FirstDeniedFinancialClass": row[39],
#                     "FirstDeniedPayerName": row[40],
#                     "LastDeniedAmount": row[46],
#                     "LastDeniedPayerName": row[48],
#                     "LastDeniedFinancialClass": row[47],
#                     "LastDeniedReasonCode": row[50],
#                     "LastDeniedType": row[51],
#                     "LastDeniedDescription": row[52],
#                     "LastDeniedDate": row[45],
#                 }
#             )
#         cursor.close()
#         conn.close()
#         return {"type": "details", "content": results}
#     except Exception as e:
#         return str(e), 500


@app.route("/v2/get_summary/", methods=["POST", "GET"])
def get_summary():
    if request.method == "POST":
        try:
            query = request.form["query"]
            answer = request.form["answer"]
            prompt = f"""
                Make a summary about the next content according to the question.
                content: {answer}
                question: {query}
            """
            return Response(
                generate_text(OPENAI_KEY, prompt), mimetype="text/event-stream"
            )
        except Exception as e:
            return str(e), 500
    else:
        return "Method not allowed.", 405


@app.route("/v2/query_pdf/", methods=["POST", "GET"])
def chatPDF():
    if request.method == "POST":
        query = request.form["query"]
        payer = get_payer_name(query)
        print(payer)
        return chat_pdf(query, payer)
        # queryResponse = query_embedding(query, "pdf")


def get_payer_name(query):
    try:
        system_prompt = f"""
                Extract available payer name from the next content, and return just the correct payer name mentioned below, nothing else just the payer name so that I can use it in the next step. 
                For now, available payers are Aetna, Cigna, Humana, Medicare, BCBS/California, BCBS/Colorado, BCBS/Connectcut, BCBS/Georgia, BCBS/Illinois, BCBS/Indiana, BCBS/Kentucky, BCBS/Maine, BCBS/Massachusetts, BCBS/Missouri, BCBS/Nevada, BCBS/NewYork, BCBS/Ohi, BCBS/Virginia. BCBS means BlueCrossBlueShield.
                So, for example, if the extracted payer name is BlueCrossBlueShield of California, you should return 'BCBS/California', if the extdracted payer name is 'Aetnaa' assume that there was a typo, but you should return 'Aetna'.
                
                If there is no payer name mentioned above, you just return 'NULL'
                content: {query}

            """
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.1,
            stop=None,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
            ],
        )
        message = res["choices"][0]["message"]["content"]
        print(message)
        if "NULL" in message:
            return "General"
        else:
            # res = re.findall(r"\d+", res)[0]
            res = res.strip()
            return res
    except Exception as e:
        raise e


def chat_pdf(query, payer="general"):
    queryResponse = query_pinecone(query, payer)

    if not queryResponse:
        return jsonify({"message": "Querying to pinecone Error"})
    inputSentence = ""
    ids = ""
    for i in queryResponse["matches"]:
        inputSentence += i["metadata"]["content"]
        ids += i["id"]
    inputSentence = limit_string_tokens(inputSentence, 1000)
    print(ids)
    try:
        prompt = f"""
                    You are medical chatbot. You are the first AI-driven platform that fully automates the denial management process. You need to give detailed instruction about the user query according to the next Context.
                    Context: {inputSentence}
                    Query: {query}
                    And just return a response, not to start with "Answer:"
        """

        return {"type": "generic", "content": generate_text(OPENAI_KEY, prompt)}

    except Exception as e:
        print(traceback.format_exc())
        return "Net Error"


@app.route("/v2/get_payer_policy/", methods=["POST", "GET"])
def get_payer_policy():
    # queryResponse = query_embedding(query, "pdf")

    CPT = 96372

    prompt = f"""
                You are medical chatbot. You are the first AI-driven platform that fully automates the denial management process.
                You need to findout corresponding medical procedure type according to the next CPT code, DX codes, and Modifier and just return the medical procedure type so that I can use the type for further search.
                CPT code: {CPT}
                DX codes: 
                Modifier: 
    """

    completions = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=512,
        n=1,
        stop=None,
        temperature=0.1,
        seed=123,
        # stream=True,
    )
    return completions["choices"][0]["text"]
    query = ""
    queryResponse = query_embedding(query)

    if not queryResponse:
        return jsonify({"message": "Querying Embedding Error"})
    inputSentence = ""
    ids = ""
    for i in queryResponse["matches"]:
        inputSentence += i["metadata"]["content"]
        ids += i["id"]
    inputSentence = limit_string_tokens(inputSentence, 1000)
    print(ids)
    try:
        prompt = f"""
                    You are medical chatbot. You are the first AI-driven platform that fully automates the denial management process. You need to give detailed instruction about the user query.
                    Context: {inputSentence}
                    Question: {query}
        """

        return {"type": "generic", "content": generate_text(OPENAI_KEY, prompt)}
        # return Response(
        #     generate_text(OPENAI_KEY, prompt), mimetype="text/event-stream"
        # )
    except Exception as e:
        print(traceback.format_exc())
        return "Net Error"


def generate_text(openAI_key, prompt, engine="text-davinci-003"):
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=0.1,
        stop=None,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
        ],
    )
    message = res["choices"][0]["message"]["content"]
    return message
    # for event in completions:
    #     event_text = event["choices"][0]["text"]
    #     yield event_text


def limit_string_tokens(string, max_tokens):
    tokens = string.split()  # Split the string into tokens
    if len(tokens) <= max_tokens:
        return string  # Return the original string if it has fewer or equal tokens than the limit

    # Join the first 'max_tokens' tokens and add an ellipsis at the end
    limited_string = " ".join(tokens[:max_tokens])
    return limited_string


def creating_embedding(query):
    api_key = OPENAI_KEY
    try:
        openai.api_key = api_key

        res = openai.Embedding.create(model="text-embedding-ada-002", input=[query])

        embedding = res["data"][0]["embedding"]

        return embedding

    except Exception as e:
        print(traceback.format_exc())

        return []


def query_pinecone(query, payer):
    sentences, embeddings, vec_indexes = get_embedding([query])
    if len(embeddings) == 0:
        return jsonify({"message": "Creating Embedding Error"})
    try:
        query_res = PINECONE_INDEX.query(
            top_k=5,
            include_values=True,
            include_metadata=True,
            vector=embeddings[0],
            namespace=payer,
        )
        print("query res", query_res)
        return query_res
        # grouped_sentences = {}
        # for result in query_res['matches']:
        #     vector_id = result['id']
        #     file_name = re.search(r"vec\d+-(.+)\.pdf", vector_id).group(1)
        #     print(file_name)
        #     if file_name not in grouped_sentences:
        #         grouped_sentences[file_name] = []
        #     grouped_sentences[file_name].append(result['metadata']['sentence'])

        # return grouped_sentences

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"message": "Error in Pinecone"})


def get_embedding(content):
    try:
        apiKey = OPENAI_KEY
        openai.api_key = apiKey
        response = openai.Embedding.create(
            model="text-embedding-ada-002", input=content
        )
        embedding = []
        vec_indexes = []
        index = 0
        for i in response["data"]:
            index += 1
            embedding.append(i["embedding"])
            vec_indexes.append("vec" + str(index))
        return content, embedding, vec_indexes
    except Exception as e:
        print(traceback.format_exc())
        return [], [], []


# @app.route("/v2/get-overview/", methods=["POST", "GET"])
# def get_overview():
#     if request.method == "GET":
#         res = {}
#         conn = sqlite3.connect("./static/database.db")
#         cursor = conn.cursor()
#         query = """SELECT
#                         COUNT(*) AS nClaims,
#                         SUM(CASE WHEN Payments > 0 THEN 1 ELSE 0 END) AS nPaidClaims,
#                         SUM(CASE WHEN Payments = 0 THEN 1 ELSE 0 END) AS nUnpaidClaims,
#                         strftime('%Y-%m', DateOfService) AS month
#                     FROM
#                         MainData
#                     GROUP BY
#                         month
#                     ORDER BY
#                         month
#         """
#         cursor.execute(query)
#         rows = cursor.fetchall()
#         claims = 0
#         paid_claims = 0
#         unpaid_claims = 0
#         for row in rows:
#             claims += row[0]
#             paid_claims += row[1]
#             unpaid_claims += row[2]
#         res["total"] = rows
#         res["claims"] = claims
#         res["paid_claims"] = paid_claims
#         res["unpaid_claims"] = unpaid_claims
#         cursor.close()
#         conn.close()

#         return res


######################9.1 new flow###############################
denial_info = ""


def check_query_type(query):
    try:
        prompt = f"""
                Extract claim number from the next content, and return just the claim number, nothing else just the claim number so that I can use it in the next step. If there is no claim number, you just return 'NULL'
                content: {query}

            """
        openai.api_key = OPENAI_KEY
        completions = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=512,
            n=1,
            stop=None,
            temperature=0.1,
            seed=123,
        )
        print(completions)
        res = completions["choices"][0]["text"]
        if "NULL" in res:
            return "Generic"
        else:
            res = re.findall(r"\d+", res)[0]
            return res
    except Exception as e:
        raise e


def chat_generic(query):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.1,
            stop=None,
            messages=[
                {
                    "role": "system",
                    "content": f"""
                        You are medical chatbot. You are the first AI-driven platform that fully automates the denial management process.
                    """,
                },
                {"role": "user", "content": query},
            ],
        )
        message = res["choices"][0]["message"]["content"]
        print(message)

        return message
    except Exception as e:
        return str(e), 500


def chat_specific(all_info):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.1,
            stop=None,
            messages=[
                {
                    "role": "system",
                    "content": f"""
                        You are medical chatbot. You are the first AI-driven platform that fully automates the denial management process.
                        Claim Info: {all_info}
                        You have to refer the above Claim Info to generate professional guide how to recover the denied claim.
                        You can find many of valuable information from the Claim Info such as DateOfService, Payers, AppointmentType, financial infos, Provider, Denied Code and Description, Procedure codes, diagnosis codes, Patient history info, etc.
                        Depends on these information, give professional guidance about why the claim denied and what should do to recover it if it is recoverable.
                        If you can't fine any information related to claim denial, you can respond that the given claim is not denied one.
                    """,
                },
            ],
        )
        message = res["choices"][0]["message"]["content"]
        print(message)

        return message
    except Exception as e:
        return str(e), 500


# @app.route("/v2/query_start/", methods=["POST", "GET"])
# def start():
#     try:
#         if request.method == "POST":
#             query = request.form["query"]
#             print(query)
#             query_type = check_query_type(query)
#             if query_type == "Generic":
#                 response = chat_generic(query)
#                 return {"type": "generic", "content": response}
#             ############# when the response indicates claim number ##############
#             """
#                 From claimid, get PatientID, PrimaryPayer, SecondaryPayer, ServiceProvider, CPT codes, carc & rarc codes
#                 "SELECT DateOfService, ChargeProcessDate, PrimaryPayer, SecondaryPayer, AppointmentType, ServiceProvider, DeniedDate, DeniedPayerName, DeniedCARC, DeniedRARC, DeniedType, DeniedDescription, PatientID"
#             """
#             print(query_type)
#             global denial_info
#             denial_info = get_denial_info(query_type)
#             print("denial info", denial_info)
#             patient_id = denial_info[0]["PatientID"]
#             claim_id = denial_info[0]["ClaimID"]
#             return {"type": "specific", "claim_id": claim_id}
#             patient_history = get_patient_history(patient_id)
#             procedures = get_procedures(claim_id)
#             modifiers = get_modifiers(claim_id)

#             all_info = ""
#             all_info += f"Denial Info:\n{json.dumps(denial_info)}\n\n"
#             all_info += f"Patient History:\n{json.dumps(patient_history)}\n\n"
#             all_info += f"Procedures:\n{json.dumps(procedures)}\n\n"
#             all_info += f"Modifiers:\n{json.dumps(modifiers)}\n"
#             res = chat_specific(all_info)
#             return {"type": "generic", "content": res}
#             # if denial_info[0]["DeniedRARC"] == "M127":
#             #     patient_id = denial_info[0]["PatientID"]
#             #     patient_history = get_patient_history(patient_id)
#             #     formatted_data = ""
#             #     for key, value in patient_history.items():
#             #         formatted_data += f"{key}: {value}\n"
#             #     ret = f"""
#             #         The denial detail of your claim is as follows:
#             #         DenialCode: M127
#             #         Description: {denial_info[0]["DeniedDescription"]}
#             #         The patient information it requires is here.
#             #         -------------------------------------------

#             #         {formatted_data}
#             #         Please use this info.
#             #     """
#             #     return {"type": "generic", "content": ret}
#             # if denial_info[0]["DeniedRARC"] == "CO4":
#             #     claim_id = denial_info[0]["ClaimNumber"]
#             #     procedures = get_procedures(claim_id)
#             #     modifiers = get_modifiers(claim_id)
#             #     return {"type": "generic", "content": json.dumps(procedures)}
#     except Exception as e:
#         raise e


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# def get_denial_info(claimid):
#     try:
#         sql_query = f"""SELECT
#                             c.*,  -- Select all columns from the 'claims' table
#                             (
#                                 SELECT GROUP_CONCAT(d.ICD10_Code)
#                                 FROM Diagnosis d
#                                 WHERE c.ClaimID = d.ClaimID
#                             ) AS Diagnosis_Codes,  -- Subquery to retrieve diagnosis codes as an array
#                             (
#                                 SELECT GROUP_CONCAT(p.CPT_Code)
#                                 FROM Procedures p
#                                 WHERE c.ClaimID = p.ClaimID
#                             ) AS Procedure_Codes  -- Subquery to retrieve procedure codes as an array
#                         FROM
#                             claims c
#                         WHERE
#                             c.ClaimID LIKE '%{claimid}%'  -- Replace 'your_claim_id_here' with the desired ClaimID
#                     """

#         conn = sqlite3.connect("./static/database.db")
#         cursor = conn.cursor()
#         cursor.execute(sql_query)
#         results = []

#         # Iterate over rows (each row represents a claim)
#         for row in cursor.fetchall():
#             # Create a dictionary to store claim details
#             claim_details = {
#                 "ClaimNumber": row[0],
#                 "DOS": row[1],
#                 "ChargeProcessDate": row[2],
#                 "PrimaryPayer": row[3],
#                 "SecondaryPayer": row[4],
#                 "AppointmentType": row[5],
#                 "Charges": row[6],
#                 "Payments": row[7],
#                 "Adjustments": row[8],
#                 "ServiceProvider": row[9],
#                 "DeniedDate": row[10],
#                 "DeniedAmount": row[11],
#                 "DeniedPayerName": row[12],
#                 "DeniedCARC": row[13],
#                 "DeniedRARC": row[14],
#                 "DeniedType": row[15],
#                 "DeniedDescription": row[16],
#                 "PatientID": row[17],
#                 "DiagnosisCodes": [],
#                 "CPTCodes": [],
#             }

#             # Split diagnosis codes and CPT codes by comma and add them to the respective lists
#             if row[18]:
#                 claim_details["DiagnosisCodes"] = row[18].split(",")
#             if row[19]:
#                 claim_details["CPTCodes"] = row[19].split(",")

#             # Append the claim details dictionary to the results list
#             results.append(claim_details)
#             results_text = json.dumps(results)

#         cursor.close()
#         conn.close()

#         return results
#     except Exception as e:
#         print(traceback.format_exc())
#         return "Net Error"


# def get_denial_info(claimid):
#     try:
#         # Set the custom row factory
#         conn = sqlite3.connect("./static/database.db")
#         conn.row_factory = dict_factory
#         cursor = conn.cursor()

#         sql_query = f"""SELECT
#             c.*,  -- Select all columns from the 'claims' table
#             (
#                 SELECT GROUP_CONCAT(d.ICD10_Code)
#                 FROM Diagnosis d
#                 WHERE c.ClaimID = d.ClaimID
#             ) AS Diagnosis_Codes,  -- Subquery to retrieve diagnosis codes as an array
#             (
#                 SELECT GROUP_CONCAT(p.CPT_Code)
#                 FROM Procedures p
#                 WHERE c.ClaimID = p.ClaimID
#             ) AS Procedure_Codes  -- Subquery to retrieve procedure codes as an array
#         FROM
#             claims c
#         WHERE
#             c.ClaimID LIKE '%{claimid}%'  -- Replace 'your_claim_id_here' with the desired ClaimID
#         """

#         cursor.execute(sql_query)
#         results = cursor.fetchall()

#         # Process the data and create the desired structure
#         for result in results:
#             result["DiagnosisCodes"] = (
#                 result["Diagnosis_Codes"].split(",")
#                 if result["Diagnosis_Codes"]
#                 else []
#             )
#             result["CPTCodes"] = (
#                 result["Procedure_Codes"].split(",")
#                 if result["Procedure_Codes"]
#                 else []
#             )

#         cursor.close()
#         conn.close()

#         return results
#     except Exception as e:
#         print(traceback.format_exc())
#         return "Net Error"


################# 9.15 ########################


# @app.route("/v2/confirm_payer/", methods=["POST", "GET"])
# def confirm_payer():
#     if request.method == "POST":
#         ClaimID = request.form["ClaimID"]
#     (
#         denied_payer,
#         denial_carc,
#         denial_rarc,
#         denial_description,
#         charged_amount,
#         paied_amount,
#         filing_limit,
#         denied_type,
#     ) = get_denial_information(ClaimID)
#     return {
#         "denied_payer": denied_payer,
#         "status": "success",
#     }


# @app.route("/v2/map_denial_reason/", methods=["POST", "GET"])
# def map_denial_reason():
#     if request.method == "POST":
#         ClaimID = request.form["ClaimID"]
#     (
#         denied_payer,
#         denial_carc,
#         denial_rarc,
#         denial_description,
#         charged_amount,
#         paied_amount,
#         filing_limit,
#         denied_type,
#     ) = get_denial_information(ClaimID)
#     denial_reasons = get_denial_reason(denial_carc, denial_rarc)
#     print("denial reason", denial_reasons)
#     print("denial description", denial_description)
#     return {
#         "original_reason": denial_reasons,
#         "current_reason": denial_description,
#         "denied_payer": denied_payer,
#         "denied_rarc": denial_rarc,
#         "denied_carc": denial_carc,
#         "charged_amount": charged_amount,
#         "paid_amount": paied_amount,
#         "filing_limit": filing_limit,
#         "denied_type": denied_type,
#         "status": "success",
#     }


# @app.route("/v2/get_day_to_appeal/", methods=["POST", "GET"])
# def get_day_to_appeal():
#     if request.method == "POST":
#         ClaimID = request.form["ClaimID"]
#         conn = sqlite3.connect("./static/database.db")
#         cursor = conn.cursor()
#         sql_query = f"SELECT ClaimFilingLimit, DeniedDate from Claims where ClaimID = '{ClaimID}'"

#         cursor.execute(sql_query)
#         for row in cursor.fetchall():
#             DeniedDate = row[1]
#             ClaimFilingLimit = row[0]

#         print("DeniedDate", DeniedDate)
#         print("ClaimFilingLimit", ClaimFilingLimit)
#         parsed_date = convert_to_YMD(DeniedDate)
#         if parsed_date is not None:
#             today = date.today()
#             date_difference = (today - parsed_date).days
#             day_to_appeal = 365 - date_difference
#             return {"status": "success", "days": day_to_appeal}
#         else:
#             return {
#                 "status": "error",
#                 "message": "Invalid date format or date not provided.",
#             }


def convert_to_YMD(input_date):
    try:
        # Define the input date formats you expect to handle
        input_formats = ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]

        # Try each format until one succeeds
        for format in input_formats:
            try:
                parsed_date = datetime.strptime(input_date, format)
                # Format the parsed date as 'Y-M-D'
                return parsed_date.date()
            except ValueError:
                pass

        # If none of the formats match, return None
        return None

    except Exception as e:
        print("Error:", e)


# @app.route("/v2/validate_cpt/", methods=["POST", "GET"])
# def validate_cpt():
#     if request.method == "POST":
#         ClaimID = request.form["ClaimID"]
#         payer = request.form["payer"]
#         print(payer)
#         print(len(payer))
#     cpt_codes, icd_codes, cpt_descriptions, icd_descriptions = get_cpt_icd_codes(
#         ClaimID
#     )
#     # is_exist = check_cpt_icd_code(cpt_codes, icd_codes)
#     # text_cpt_codes = ", ".join(cpt_codes)
#     (
#         is_valid,
#         applied_payer_policy,
#         required_docs,
#         policy_title,
#         recommendation,
#     ) = check_cpt_icd_valid(cpt_codes, icd_codes, payer)
#     return {
#         "CPT_Validation": is_valid,
#         "CPT_Codes": cpt_codes,
#         "ICD_Codes": icd_codes,
#         "status": "success",
#         "applied_payer_policy": applied_payer_policy,
#         "required_docs": required_docs,
#         "cpt_descriptions": cpt_descriptions,
#         "icd_descriptions": icd_descriptions,
#         "policy_title": policy_title,
#         "recommendation": recommendation,
#     }


# @app.route("/v2/get_document/", methods=["POST"])
# def get_necessary_documents():
#     try:
#         denial_code = request.form["denialCode"]
#         conn = sqlite3.connect("./static/database.db")
#         cursor = conn.cursor()
#         documents = []

#         sql_query = f"""SELECT "Document Name", Links FROM documents WHERE "Denial Remark Codes (RARC)" LIKE '%{denial_code}%'"""
#         cursor.execute(sql_query)
#         for row in cursor.fetchall():
#             documents.append({"document_names": row[0], "links": row[1]})
#         if len(documents) == 0:
#             documents.append({"document_names": "No required Document", "links": ""})
#         return ({"documents": documents, "status": "success"}), 200
#         # If all codes are found, return True
#         conn.close()

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@app.route("/v2/generate_appeal/", methods=["POST"])
def generate_appeal():
    try:
        all_info = request.form["all_Info"]

        print(all_info)

        prompt = f"""
            Generate professional appeal letter that contains less than 1000 words for the denied claim with the next information.
            You can find Insurance Company Name, Claim Number, etc in the following information.
            And this appeal letter is from 'Gabeo Corp'
            Infomation for appeal letter: {all_info}

        """

        completions = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=512,
            n=1,
            stop=None,
            temperature=0.1,
            seed=123,
            # stream=True,
        )
        message = completions["choices"][0]["text"]
        return {"appeal": message, "status": "success"}
        print(query)

        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.1,
            stop=None,
            messages=[
                {
                    "role": "system",
                    "content": query,
                },
                {"role": "user", "content": "generate appeal letter"},
            ],
        )
        message = res["choices"][0]["message"]["content"]

        return {"appeal": message, "status": "success"}
    except Exception as e:
        raise e


@app.route("/v2/parse_edi/", methods=["POST"])
def parse_edi():
    try:
        edi = request.form["edi"]
        path = "./uploads/edi.txt"
        with open(path, "w") as file:
            file.write(edi)

        transaction_set = parse(path)
        data = transaction_set.to_dataframe()

        records = data.to_json(orient="records")
        print(records)
        ###save to db###
        # conn = sqlite3.connect("./static/database.db")
        # cursor = conn.cursor()

        # parsed_records = json.loads(records)  # Load the JSON string into a Python list
        # for entry in parsed_records:  # Now iterate over the list
        #     cursor.execute(
        #         """
        #         INSERT INTO edi_claims   (
        #             marker, patient, code, modifier, qualifier,
        #             allowed_units, billed_units, transaction_date, charge_amount, allowed_amount,
        #             paid_amount, payer, start_date, end_date, rendering_provider,
        #             payer_classification, adj_0_amount, adj_0_code, adj_0_group
        #         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        #     """,
        #         (
        #             entry["marker"],
        #             entry["patient"],
        #             entry["code"],
        #             entry["modifier"],
        #             entry["qualifier"],
        #             entry["allowed_units"],
        #             entry["billed_units"],
        #             entry["transaction_date"],
        #             entry["charge_amount"],
        #             entry["allowed_amount"],
        #             entry["paid_amount"],
        #             entry["payer_city"],
        #             entry["start_date"],
        #             entry["end_date"],
        #             entry["rendering_provider"],
        #             entry["payer_classification"],
        #             entry["payer_name"],
        #             entry["payer_city"],
        #             entry["payer_state"],
        #             entry["payer_zipcode"],
        #             entry["payee_name"],
        #             entry["payee_city"],
        #             entry["payee_state"],
        #             entry["payee_zipcode"],
        #             entry["payee_npi"],
        #             entry["patient_id"],
        #             entry["patient_firstname"],
        #             entry["patient_lastname"],
        #             entry["adj_0_amount"],
        #             entry["adj_0_code"],
        #             entry["adj_0_group"],
        #         ),
        #     )

        # Commit the changes and close the connection
        # conn.commit()
        # conn.close()
        #####################

        return data.to_json(orient="records"), 200
        # return data_list
        # print(type(response.data))
        # return response
    except Exception as e:
        raise e
        return "edi parsing error"


# def check_cpt_icd_valid(cpt_codes, icd_codes, payer):
#     cpt_descriptions = get_cpt_descriptions(cpt_codes)
#     cpt_info = []
#     for i in range(len(cpt_codes)):
#         cpt_info.append(
#             {"cpt_code": cpt_codes[i], "cpt_description": cpt_descriptions[i]}
#         )
#     str_cpt_info = str(cpt_info)
#     str_icd_info = str(icd_codes)
#     pinecone_prompt = f"""
#                     Tell me when {str_cpt_info} with {str_icd_info} be covered
#                 """
#     query_res = query_pinecone(pinecone_prompt, payer)
#     if not query_res:
#         return jsonify({"message": "Querying to pinecone Error"})
#     content = ""
#     ids = ""
#     for i in query_res["matches"]:
#         content += i["metadata"]["content"]
#         ids += i["id"]
#     content = limit_string_tokens(content, 2000)
#     print(f"Are {str_cpt_info} with {str_icd_info} medically necessary?")
#     print("content", content)

#     try:
#         res = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             temperature=0.1,
#             stop=None,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": f"""
#                         You are a "TRUE" or "FALSE" generator.
#                         You need to use next Content to generate "TRUE" or "FALSE" for the user query.
#                         Content: {content}
#                         If you can't find relative information from the content, it means the given CPT codes are not valid.
#                         So in this case, you return "FALSE"
#                     """,
#                 },
#                 {
#                     "role": "user",
#                     "content": f"Are {str_cpt_info} with {str_icd_info} medically necessary?",
#                 },
#             ],
#         )
#         message = res["choices"][0]["message"]["content"]
#         applied_payer_policy = chat_pdf(
#             f"Tell me under what kind of conditions {str_cpt_info} with {str_icd_info} be covered? Write all the conditions as a list",
#             payer,
#         )

#         policy_title = chat_pdf(
#             f"What is the LCD title for this policy? {applied_payer_policy} Return just the title",
#             payer,
#         )

#         required_docs = chat_pdf(
#             f"What is the required document for {str_cpt_info} with {str_icd_info}?",
#             payer,
#         )
#         recommendation = chat_pdf(
#             f"What is needed {str_cpt_info} with {str_icd_info} to be covered and medically necessary?",
#             payer,
#         )
#         return (
#             message,
#             applied_payer_policy,
#             required_docs,
#             policy_title,
#             recommendation,
#         )
#     except Exception as e:
#         raise e


# def check_cpt_icd_code(cpt_codes, icd_codes):
#     conn = sqlite3.connect("./static/database.db")
#     cursor = conn.cursor()

#     for cpt_code in cpt_codes:
#         sql_query = f"SELECT COUNT(*) FROM CPT_Details WHERE CPT_Code = '{cpt_code}'"
#         cursor.execute(sql_query)
#         count = cursor.fetchone()[0]
#         if count == 0:
#             # If any code is not found, return False immediately
#             conn.close()
#             return False
#     for icd_code in icd_codes:
#         sql_query = f"SELECT COUNT(*) FROM Diagnosis WHERE ICD10_Code = '{icd_code}'"
#         cursor.execute(sql_query)
#         count = cursor.fetchone()[0]
#         if count == 0:
#             # If any code is not found, return False immediately
#             conn.close()
#             return False

#     # If all codes are found, return True
#     conn.close()
#     return True


# def get_cpt_icd_codes(ClaimID):
#     sql_query = f"SELECT CPT_Code from Procedures where ClaimID = {ClaimID}"
#     conn = sqlite3.connect("./static/database.db")
#     cursor = conn.cursor()
#     cursor.execute(sql_query)
#     CPT_Codes = []
#     for row in cursor.fetchall():
#         CPT_Codes.append(row[0])
#     print(CPT_Codes)
#     CPT_Descriptions = get_cpt_descriptions(CPT_Codes)

#     sql_query = f"SELECT ICD10_Code from Diagnosis where ClaimID = {ClaimID}"
#     cursor.execute(sql_query)
#     ICD_Codes = []
#     for row in cursor.fetchall():
#         ICD_Codes.append(row[0])
#     print("asdfasdfasdf", ICD_Codes)
#     ICD_Descriptions = get_icd_descriptions(ICD_Codes)

#     cursor.close()
#     conn.close()
#     return CPT_Codes, ICD_Codes, CPT_Descriptions, ICD_Descriptions


# def get_cpt_descriptions(cpt_codes):
#     try:
#         conn = sqlite3.connect("./static/database.db")
#         cursor = conn.cursor()
#         cpt_descriptions = []
#         for cpt_code in cpt_codes:
#             sql_query = (
#                 f"SELECT CPT_Description from CPT_Details where CPT_Code = '{cpt_code}'"
#             )

#             cursor.execute(sql_query)
#             cpt_description = cursor.fetchone()[0]
#             cpt_descriptions.append(cpt_description)
#         cursor.close()
#         conn.close()
#         return cpt_descriptions
#     except Exception as e:
#         print(str(e))
#         return "CPT code is not listed yet."


# def get_icd_descriptions(icd_codes):
#     try:
#         conn = sqlite3.connect("./static/database.db")
#         cursor = conn.cursor()
#         icd_descriptions = []
#         for icd_code in icd_codes:
#             sql_query = (
#                 f"SELECT WHO_Full_Desc from ICD10 where ICD10_Code = '{icd_code}'"
#             )
#             cursor.execute(sql_query)
#             icd_description = cursor.fetchone()[0]
#             icd_descriptions.append(icd_description)
#         cursor.close()
#         conn.close()
#         return icd_descriptions
#     except Exception as e:
#         print(str(e))
#         return "ICD code is not listed yet."


# def get_denial_reason(denial_carc, denial_rarc):
#     print("carc, rarc codes", denial_carc, denial_rarc)
#     sql_query = f"SELECT REMARK_TYPE, DESCRIPTION from claim_adjustment_reasons where REMITTANCE_CODE = '{denial_carc}' or REMITTANCE_CODE = '{denial_rarc}'"
#     conn = sqlite3.connect("./static/database.db")
#     cursor = conn.cursor()
#     cursor.execute(sql_query)
#     descriptions = []
#     for row in cursor.fetchall():
#         descriptions.append({"remark_type": row[0], "description": row[1]})
#     cursor.close()
#     conn.close()
#     return descriptions


# def get_denial_information(ClaimID):
#     sql_query = f"SELECT DeniedPayerName, CARC, RARC, DeniedDescription, Charges, Payments, ClaimFilingLimit, DeniedType from Claims where ClaimID = {ClaimID}"
#     conn = sqlite3.connect("./static/database.db")
#     cursor = conn.cursor()
#     cursor.execute(sql_query)

#     for row in cursor.fetchall():
#         denied_payer = row[0]
#         denied_carc = row[1]
#         denied_rarc = row[2]
#         denied_description = row[3]
#         charged_amount = row[4]
#         paied_amount = row[5]
#         filing_limit = row[6]
#         denied_type = row[7]
#     cursor.close()
#     conn.close()
#     return (
#         denied_payer,
#         denied_carc,
#         denied_rarc,
#         denied_description,
#         charged_amount,
#         paied_amount,
#         filing_limit,
#         denied_type,
#     )


# def get_payers(ClaimID):
#     sql_query = (
#         f"SELECT PrimaryPayer, DeniedPayerName from Claims where ClaimID = {ClaimID}"
#     )
#     conn = sqlite3.connect("./static/database.db")
#     cursor = conn.cursor()
#     cursor.execute(sql_query)

#     for row in cursor.fetchall():
#         primary_payer = row[0]
#         denied_payer = row[1]
#     cursor.close()
#     conn.close()
#     return primary_payer, denied_payer


# @app.route("/v2/getclaim/", methods=["POST", "GET"])
# def getClaim():
#     if request.method == "POST":
#         ClaimID = request.form["ClaimID"]
#     return {
#         "claim": claims.find({"claimid": ClaimID}),
#         "status": "success",
#     }


# @app.route("/v2/getNDC", methods=["POST"])
# def getNDCList():
#     ClaimID = request.form["ClaimID"]
#     print("Cliam -> ", ClaimID)

#     sql_query = f"SELECT DoctorNote FROM Claims WHERE ClaimID = ${ClaimID}"
#     print(sql_query)
#     conn = sqlite3.connect("./static/database.db")
#     cursor = conn.cursor()
#     cursor.execute(sql_query)
#     DoctorNote = cursor.fetchone()

#     print("HHH: ", DoctorNote)

#     sql_query = (
#         "SELECT * FROM ndc_hcpcs WHERE " + '"HCPCS Description"' + f" = '${DoctorNote}'"
#     )
#     cursor.execute(sql_query)
#     matched_list = cursor.fetchall()
#     print("matched records: ", matched_list)

#     cursor.close()
#     conn.close()
#     return str(matched_list)


if __name__ == "__main__":
    app.run(debug=True)
