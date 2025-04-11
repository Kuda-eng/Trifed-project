from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from twilio.rest import Client
import os

app = FastAPI()

# Twilio Credentials
TWILIO_ACCOUNT_SID = TWILIO_ACCOUNT_SID = "AC2a6911ff58bb9290ce1129a2dda8e55e"
TWILIO_AUTH_TOKEN = "919908d58a8c0d07b1e0f1df185d72b9"
TWILIO_WHATSAPP_NUMBER = "+15557231185"

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# MongoDB Setup
MONGO_URI = "mongodb+srv://mhanduk2:woi24Njv7r0NTkSk@cluster0.z79xv.mongodb.net/?retryWrites=true&w=majority&tls=true"
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["whatsapp_bot"]
campers_collection = db["campers"]

MESSAGES = {
    "welcome": "Welcome to NZC Mhondoro Junction April 2025 Camper Registration! Please enter your full name:",
    "ask_age": "Thanks {name}! Please enter your age:",
    "ask_gender": "Great, please enter your gender (Male/Female):",
    "ask_contact": "Well done, Please enter your contact number:",
    "ask_church": "Please enter your church name:",
    "ask_federation": "Brilliant you're doing great, please enter your federation name:",
    "ask_next_of_kin_name": "Almost done, please enter your next of kin's full name:",
    "ask_next_of_kin_relationship": "Please enter your next of kin’s relationship to you:",
    "ask_next_of_kin_contact": "Lastly, please enter your next of kin’s contact number:",
    "review": "Amazing, Please review your details:\nName: {name}\nAge: {age}\nGender: {gender}\nContact: {contact}\nChurch: {church}\nFederation: {federation}\nNext of Kin: {kin_name}\nRelationship: {kin_relationship}\nNext of Kin Contact: {kin_contact}\nType 'confirm' to complete registration, 'edit' to modify, or 'cancel' to discard.",
    "completed": "Registration complete! Thank you, {name}.",
    "invalid_input": "Invalid input. Please try again.",
    "edit_prompt": "Please specify the field you want to edit: Name, Age, Gender, Contact, Church, Federation, Next of Kin Name, Next of Kin Relationship, or Next of Kin Contact.",
}

VALID_GENDERS = ["male", "female"]
VALID_FEDERATIONS = ["chyfed", "mhondoro", "glengate", "highnorrah"]

@app.post("/webhook")
async def twilio_webhook(From: str = Form(...), Body: str = Form(...)):
    sender_id = From
    message_text = Body.strip()
    camper = campers_collection.find_one({"phone": sender_id})

    if not camper:
        camper = {"phone": sender_id, "status": "awaiting_name"}
        campers_collection.insert_one(camper)
        send_message(sender_id, MESSAGES["welcome"])
    else:
        handle_registration_steps(camper, sender_id, message_text)

    return JSONResponse(content={"status": "received"}, status_code=200)

def handle_registration_steps(camper, sender_id, message_text):
    status = camper.get("status")
    
    if status == "awaiting_name":
        campers_collection.update_one({"phone": sender_id}, {"$set": {"name": message_text, "status": "awaiting_age"}})
        send_message(sender_id, MESSAGES["ask_age"].format(name=message_text))
    elif status == "awaiting_age" and message_text.isdigit() and 0 < int(message_text) < 120:
        campers_collection.update_one({"phone": sender_id}, {"$set": {"age": int(message_text), "status": "awaiting_gender"}})
        send_message(sender_id, MESSAGES["ask_gender"])
    elif status == "awaiting_gender" and message_text.lower() in VALID_GENDERS:
        campers_collection.update_one({"phone": sender_id}, {"$set": {"gender": message_text.title(), "status": "awaiting_contact"}})
        send_message(sender_id, MESSAGES["ask_contact"])
    elif status == "awaiting_contact":
        campers_collection.update_one({"phone": sender_id}, {"$set": {"contact": message_text, "status": "awaiting_church"}})
        send_message(sender_id, MESSAGES["ask_church"])
    elif status == "awaiting_church":
        campers_collection.update_one({"phone": sender_id}, {"$set": {"church": message_text, "status": "awaiting_federation"}})
        send_message(sender_id, MESSAGES["ask_federation"])
    elif status == "awaiting_federation" and message_text.lower() in VALID_FEDERATIONS:
        campers_collection.update_one({"phone": sender_id}, {"$set": {"federation": message_text.title(), "status": "awaiting_next_of_kin_name"}})
        send_message(sender_id, MESSAGES["ask_next_of_kin_name"])
    elif status == "review" and message_text.lower() == "confirm":
        campers_collection.update_one({"phone": sender_id}, {"$set": {"status": "registered"}})
        send_message(sender_id, MESSAGES["completed"].format(name=camper["name"]))

def send_message(to, message):
    twilio_client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        body=message,
        to=to
    )
