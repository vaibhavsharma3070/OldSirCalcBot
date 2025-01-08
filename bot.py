import json
import time
import re
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from typing import Dict, List



# group_messages = {}
# JAINA_GROUP_IDS = {-4511533778, -4565086327, -4595774021}
# OUR_BETS_GROUP_IDS = {-4778983212}
# KIOSK_GROUP_IDS = {-4575247224}  # Replace with actual Kiosk group ID

group_messages = {}
JAINA_GROUP_IDS = {-4511533778, -4565086327, -4595774021}
OUR_BETS_GROUP_IDS = {-4778983212}
KIOSK_GROUP_IDS = {}

def process_compiled_messages(compiled_messages):
    from collections import defaultdict
    
    bets = defaultdict(list)
    current_bet_type = None
    current_bet_id = None
    
    lines = compiled_messages.splitlines()
    
    print("Starting to process compiled messages...")
    for line in lines:
        line = line.strip().strip('/n')
        print(f"Processing line: {line}")  # Print every line being processed
        
        if not line:
            continue  # Skip empty lines
        
        if line.startswith('*'):
            current_bet_id = line.strip()
            print(f"Detected bet ID: {current_bet_id}")  # Print when bet ID is detected
            
        elif ':' in line and '@' not in line:
            current_bet_type = line.strip().lower().replace(':', '').strip()
            print(f"Detected bet type: {current_bet_type}")  # Print when bet type is detected
            
        elif '@' in line:
            print(f"Processing bet line: {line}")
            
            if not current_bet_type or not current_bet_id:
                print("Missing current_bet_type or current_bet_id, skipping line.")
                continue
            
            parts = line.split('@')
            if len(parts) != 2:
                print("Invalid format, skipping line.")
                continue
            
            try:
                amount = parse_amount(parts[0])
                odds = float(parts[1])
                bet_type = (
                    'Jaina' if 'jaina' in current_bet_type else 
                    'Kiosk' if 'kiosk' in current_bet_type else 
                    'our_bets'
                )
                print(f"Adding bet - Type: {bet_type}, Amount: {amount}, Odds: {odds}")  # Show bet details
                if current_bet_id:
                    bets[current_bet_id].append({'type': bet_type, 'amount': amount, 'odds': odds})
            except ValueError:
                print("Failed to parse amount or odds, skipping line.")
                continue
    
    print("Finished processing messages. Bets dictionary:")
    print(bets)  # Print the entire bets dictionary
    
    return process_bets(bets)

async def calculate_command(update, context):
    command_text = ' '.join(context.args)
    parts = command_text.split(',')
    compiled_messages = {'jaina': [], 'our_bets': [], 'kiosk': []}
    
    print(f"Command text: {command_text}")  # Log the command
    print(f"Parts: {parts}")  # Log parsed parts of the command
    
    for part in parts:
        part = part.strip()
        print(f"Searching for: '{part}'")
        
        for group_id in group_messages:
            print(f"Checking group ID: {group_id} (Type: {type(group_id)})")
            for message in group_messages[group_id]:
                if message.get('text') and part.lower() in message['text'].lower():
                    print(f"Match found: '{message['text']}'")  # Log when a match is found
                    group_id = int(group_id)  # Ensure group_id is an integer
                    if group_id in JAINA_GROUP_IDS:
                        print("Appending to Jaina")
                        compiled_messages['jaina'].append(message['text'])
                    elif group_id in OUR_BETS_GROUP_IDS:
                        print("Appending to Our Bets")
                        compiled_messages['our_bets'].append(message['text'])
                    elif group_id in KIOSK_GROUP_IDS:
                        print("Appending to Kiosk")
                        compiled_messages['kiosk'].append(message['text'])
                else:
                    print(f"Warning: message['text'] is None for message {message}")

    response = ""

    if compiled_messages['jaina']:
        response += "\njaina:\n"
        for msg in compiled_messages['jaina'] :
            response += f"{msg}\n\n"
        print("Jaina messages compiled.")  # Log when Jaina messages are compiled
    
    if compiled_messages['our_bets']:
        response += "\nour bets:\n"
        for msg in compiled_messages['our_bets']:
            response += f"{msg}\n\n"
        print("Our Bets messages compiled.")  # Log when Our Bets messages are compiled
    
    if compiled_messages['kiosk']:
        response += "\nkiosk:\n"
        for msg in compiled_messages['kiosk']:
            response += f"{msg}\n\n"
        print("Kiosk messages compiled.")  # Log when Kiosk messages are compiled

    final_output, keyword_totals = process_compiled_messages(response)
    
    if final_output:
        response = "Final Output:\n\n" + '\n'.join(final_output)
        response += "\n-------------\nFINAL SUMS:\n"
        for keyword, total in keyword_totals.items():
            response += f"*{keyword}: {int(total)}\n"
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("No valid bets found.")


# JSON file path
json_file_path = 'group_messages.json'

async def group_message_handler(update: Update, context):
    group_id = str(update.message.chat_id)
    print(f"GID:{group_id}")
    store_message(group_id, update.message)
# Load the stored messages when the bot starts
def load_messages():
    global group_messages
    try:
        with open(json_file_path, 'r') as file:
            group_messages = json.load(file)
    except FileNotFoundError:
        save_messages()

def save_messages():
    with open(json_file_path, 'w') as file:
        json.dump(group_messages, file)

def clean_old_messages():
    current_time = time.time()
    for group_id in group_messages:
        group_messages[group_id] = [msg for msg in group_messages[group_id] if current_time - msg['date'] <= 86400]  # 24 hours
    save_messages()

def store_message(group_id, message):
    if group_id not in group_messages:
        group_messages[group_id] = []

    group_messages[group_id].append({
        'message_id': message.message_id,
        'text': message.text,
        'from_user': message.from_user.username,
        'date': message.date.timestamp()  # Use timestamp to store as a numeric value
    })
    print(f"Message stored for group {group_id}: {message.text}")  # Added line
    print(f"Current group messages: {group_messages}")  # Added line to print all messages
    save_messages()
    clean_old_messages()


def parse_amount(amount_str):
    # Convert strings like '1.8k' to numeric values
    amount_str = amount_str.replace(' ', '')
    if 'k' in amount_str.lower():
        return float(amount_str.lower().replace('k', '')) * 1000
    return float(amount_str)

def weighted_average(bets):
    # Calculate weighted average odds
    total_amount = sum(bet['amount'] for bet in bets)
    weighted_sum = sum(bet['amount'] * bet['odds'] for bet in bets)
    return round(weighted_sum / total_amount, 1) if total_amount > 0 else 0

def extract_keyword(bet_id):
    # Extracts the main keyword, ignoring specifics like 'u54.5', '-13', etc.
    keyword_match = re.match(r"^\*([\w\s]+)", bet_id)
    if keyword_match:
        keyword = keyword_match.group(1).strip()
        # Handle cases where we need to generalize like 'Hawaii u54.5' -> 'Hawaii'
        keyword = re.sub(r"\s[u\d\.\-]+$", "", keyword)
        return keyword
    return bet_id


def process_bets(bets):
    final_results = []
    keyword_totals = defaultdict(float)
    
    for bet_id, bet_group in bets.items():
        jaina_bets = [bet for bet in bet_group if bet['type'] == 'Jaina']
        our_bets = [bet for bet in bet_group if bet['type'] == 'our_bets']
        kiosk_bets = [bet for bet in bet_group if bet['type'] == 'Kiosk']

        total_jaina_amount = sum(bet['amount'] for bet in jaina_bets) * 0.85
        total_our_amount = sum(bet['amount'] for bet in our_bets)
        total_kiosk_amount = sum(bet['amount'] for bet in kiosk_bets) * 0.75  # Kiosk keeps 25%

        total_amount = total_jaina_amount + total_our_amount + total_kiosk_amount

        combined_bets = jaina_bets + our_bets + kiosk_bets
        final_weighted_avg = weighted_average(combined_bets)
        
        final_results.append(f"{bet_id}\n{int(total_amount)} @ {final_weighted_avg}\n")

        keyword = extract_keyword(bet_id)
        keyword_totals[keyword] += total_amount

    return final_results, keyword_totals

async def start(update: Update, context):
    await update.message.reply_text('Welcome! Send me your bets in the format: "Type: amount @ odds". Mention me using @ to calculate.')


async def edited_message_handler(update: Update, context):
    try:
        group_id = str(update.edited_message.chat_id)
        message_id = update.edited_message.message_id
        print(f"Edited Message Detected: GID:{group_id}, MID:{message_id}")
        
        # Update the stored message with the new content
        for message in group_messages[group_id]:    
            if message['message_id'] == message_id:
                message['text'] = update.edited_message.text
                save_messages()
                print("Message updated successfully.")
                break

    except Exception as e:
        print(f"Error in edited_message_handler: {e}")
def main():
 
    application = Application.builder().token('7115597505:AAGZRlGIgErUf8V1mla6rJnSnT2HmthgrdU').build() #  
    # application = Application.builder().token('6973928813:AAEV6lmBwpg3eZjsu4S-Gt-9J7iOCxou5Mg').build()

    # Command to calculate based on keywords
    application.add_handler(CommandHandler("calculate", calculate_command))

    # Message handler for each group
    # application.add_handler(MessageHandler(filters.Chat(chat_id=-1002034863456), group_message_handler))
    
    #jaina 1 -4511533778
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=-4511533778) & (~filters.UpdateType.EDITED_MESSAGE),
        group_message_handler
    ))
    # jaina 2 -4565086327
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=-4565086327) & (~filters.UpdateType.EDITED_MESSAGE),
        group_message_handler
    ))
    #jaina 3 -4595774021
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=-4595774021) & (~filters.UpdateType.EDITED_MESSAGE),
        group_message_handler
    ))
    # our bets -4778983212
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=-4778983212) & (~filters.UpdateType.EDITED_MESSAGE),
        group_message_handler
    ))
    # # kiosk
    # application.add_handler(MessageHandler(
    #     filters.Chat(chat_id=-4575247224) & (~filters.UpdateType.EDITED_MESSAGE),
    #     group_message_handler
    # ))

    # Handle edited messages specifically
    application.add_handler(MessageHandler(
        filters.UpdateType.EDITED_MESSAGE,
        edited_message_handler
    ))
        # Start the bot
    application.run_polling()

if __name__ == '__main__':
    
    main()
