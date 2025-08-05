#!/usr/bin/env python
# coding: utf-8

# 📥 Unified Gmail Assistant – DWDA (Domain-Wide Delegation) Ready
# Wrapped in run_assistant() for Flask & Cloud Run deployment

def run_assistant():
    """
    Main function that runs the complete Gmail processing pipeline.
    Returns a summary string for Flask endpoint.
    """
    import os
    import google.auth
    from googleapiclient.discovery import build
    from base64 import urlsafe_b64decode
    from datetime import datetime, timedelta
    from dotenv import load_dotenv
    import openai
    from openai import OpenAI
    from notion_client import Client as NotionClient

    # === Load environment variables ===
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    NOTION_TOKEN = os.getenv("NOTION_TOKEN")
    NOTION_DB_ID = os.getenv("NOTION_DB_ID")

    if not OPENAI_API_KEY or not NOTION_TOKEN or not NOTION_DB_ID:
        raise ValueError(
            "❌ Missing one or more required environment variables: "
            "OPENAI_API_KEY, NOTION_TOKEN, NOTION_DB_ID"
        )

    # Configure OpenAI client (using new client style consistently)
    client = OpenAI(api_key=OPENAI_API_KEY)

    # === Gmail API Setup (DWDA) ===
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds, _ = google.auth.default(scopes=SCOPES)
    service = build("gmail", "v1", credentials=creds)
    print("✅ Gmail API authenticated via DWDA service account.")

    # === Helper Functions ===
    def extract_text_from_parts(parts):
        """Extract text content from Gmail message parts"""
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part["body"].get("data")
                if data:
                    return urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            elif "parts" in part:
                return extract_text_from_parts(part["parts"])
        return ""

    def detect_language(text):
        """Detect the language of email content using OpenAI"""
        prompt = f"What language is this email written in?\n\n{text[:500]}\n\nReply with only the language name."
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "[Error]"

    def summarize_email_multilingual(body, language):
        """Generate multilingual summary of email content"""
        prompt = f"""You are a smart assistant. Summarize the email below in a clear, short paragraph (3–5 lines) for a team inbox dashboard.

Write the summary in this language: **{language}**

EMAIL:
---
{body}
---
SUMMARY:"""
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "[Summary Error]"

    # === Command Classification ===
    COMMAND_LIST = [
        # Business / Ops
        "send_invoice", "billing_question", "pricing_request", "follow_up", "general_question",
        "account_closure", "update_contact", "change_account_details", "duplicate_request",
        # Marketing / CRM
        "unsubscribe", "feedback_positive", "complaint", "feature_request", "partnership_request",
        "event_registration", "customer_testimonial",
        # HR / Recruiting
        "job_application", "referral_submission", "interview_schedule_request", "cv_update_request",
        # Legal / Compliance
        "legal_inquiry", "contract_request", "privacy_policy_question", "data_deletion_request",
        # IT / Tech Support
        "technical_issue", "access_request", "reset_password", "security_alert", "bug_report", "system_down",
        # Logistics / Supply Chain
        "shipping_issue", "delivery_update_request", "return_request", "inventory_request",
        # Sales / Client Relations
        "schedule_demo", "confirm_availability", "send_proposal", "renew_contract", "custom_plan_request",
        # Docs / Resources
        "file_request", "request_report", "request_presentation", "send_agreement",
        # Meta
        "forward_to_support", "no_action"
    ]

    def classify_multiple_commands(subject, summary, language="English"):
        """Classify email commands using OpenAI"""
        prompt = f"""You are a multilingual business email classifier. Your task is to detect all valid commands (tasks or intents) from a business email based on the subject and summary provided.

COMMAND LIST:
{", ".join(COMMAND_LIST)}

RULES:
- Output should be a Python list of command strings (lowercase) such as ["send_invoice", "follow_up"].
- Only include commands that are clearly mentioned or strongly implied.
- Do not invent commands outside the list.
- If no clear command exists, return only: ["no_action"]
- Language of the email: {language}

EMAIL SUBJECT:
"{subject}"

EMAIL SUMMARY:
"{summary}"

COMMANDS:"""
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            output = response.choices[0].message.content.strip()
            commands = eval(output) if output.startswith("[") else []
            return [cmd for cmd in commands if cmd in COMMAND_LIST]
        except Exception:
            return ["[Error]"]

    def generate_reply_drafts(subject, body, commands, language):
        """Generate two versions of email replies"""
        if not commands or "no_action" in commands:
            return "[Skipped – Not a business-relevant message]", "[Skipped – Not a business-relevant message]"

        prompt_common = f"""
You are a professional email assistant representing a modern or multi-departmental company.
Your job is to write a helpful, human-readable, thoughtful, and accurate replies based on the user's original message.

You may be replying to:
- A customer or external partner (support, inquiries, feedback)
- A job applicant or contractor
- An internal employee (to HR, to CEO, to teammate)
- A request from management, a department, or executive team

Only generate a reply if the email appears to be:
✅ A real question, request, follow-up, or communication between people
✅ Related to company services, tasks, roles, schedules, reports, projects, hiring, policies

Do NOT generate a reply if:
❌ It's a system notification, marketing ad, newsletter, or automated alert
❌ It's from platforms like Google, Zoom, GitHub, LinkedIn, or Outlook auto-notifications
❌ The email is not clearly written by a person with intent

If the message is NOT appropriate for a human-written business reply, return exactly: [SKIP]

Context:
Language: {language}
Subject: {subject}
Commands: {', '.join(commands)}

Original Email:
---
{body}
---

Guidelines:
- Write in the same language as the email ({language}).
- Cover all user requests naturally (if more than one).
- Avoid copying the user's email content.
- Be warm but professional. Clear and to-the-point.
- Keep each reply around 3–6 sentences.
- Close with a relevant polite sign-off (optional: your name or company).
"""

        # First version (Formal tone)
        prompt_v1 = prompt_common + "\nTone: Professional and clear.\n\nReply:"
        # Second version (Friendly + collaborative)
        prompt_v2 = prompt_common + "\nTone: Friendly and supportive.\n\nReply:"

        try:
            response_1 = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_v1}],
                temperature=0.4,
                max_tokens=400
            )
            draft1 = response_1.choices[0].message.content.strip()

            response_2 = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_v2}],
                temperature=0.6,
                max_tokens=400
            )
            draft2 = response_2.choices[0].message.content.strip()

            return draft1, draft2

        except Exception as e:
            error_msg = f"[Reply Error: {str(e)}]"
            return error_msg, error_msg

    def detect_tone(body, language="English"):
        """Detect emotional tone of email"""
        prompt = f"""
You are a tone analysis expert.

Please classify the emotional tone of the following email in one word:
Choose only from: positive, neutral, negative, mixed

Language: {language}

EMAIL:
---
{body}
---

TONE:"""
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip().lower()
        except:
            return "unknown"

    def estimate_reply_confidence(draft, commands):
        """Estimate confidence score for reply quality"""
        if not draft or "[skip" in draft.lower() or "[reply error" in draft.lower():
            return 0
        if "no_action" in commands:
            return 20
        # Basic heuristic logic
        score = 60
        if any(kw in draft.lower() for kw in ["let us know", "please find", "thank you", "i've forwarded", "attached", "we appreciate"]):
            score += 20
        if len(draft.split()) > 60:
            score += 10
        return min(score, 100)

    def determine_action_taken(email):
        """Determine what action was taken on the email"""
        if "[skip" in email.get("reply_draft_1", "").lower():
            return {"name": "Skipped", "color": "gray"}
        if "reply_error" in email.get("reply_draft_1", "").lower():
            return {"name": "Error", "color": "red"}
        return {"name": "Drafted Reply", "color": "orange"}

    def determine_team_tag(commands):
        """Determine which team should handle the email"""
        tags = []
        for cmd in commands:
            if cmd in ["schedule_demo", "send_proposal", "custom_plan_request"]:
                tags.append("Sales")
            elif cmd in ["technical_issue", "bug_report", "access_request"]:
                tags.append("Support")
            elif cmd in ["job_application", "cv_update_request", "hr_query"]:
                tags.append("HR")
            elif cmd in ["contract_request", "legal_inquiry"]:
                tags.append("Legal")
            elif cmd in ["shipping_issue", "inventory_request"]:
                tags.append("Ops")
        return list(set(tags)) or ["General"]

    # === Main Processing Pipeline ===
    
    # Step 1: Fetch emails from last 7 days
    now = datetime.utcnow()
    past = (now - timedelta(days=7)).strftime('%Y/%m/%d')
    query = f"after:{past} in:inbox"

    fetched_emails = []
    threads = service.users().threads().list(userId='me', q=query, maxResults=50).execute().get('threads', [])
    print(f"📬 Found {len(threads)} threads...\n")

    # Step 2: Process each thread
    for thread in threads:
        try:
            msg = service.users().messages().get(userId='me', id=thread['id']).execute()
            payload = msg['payload']
            headers = {h['name']: h['value'] for h in payload['headers']}

            subject = headers.get("Subject", "(No Subject)")
            sender = headers.get("From", "")
            timestamp = int(msg.get("internalDate")) / 1000
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            body = extract_text_from_parts(payload.get("parts", [])) or "[No text content]"
            language = detect_language(body)

            fetched_emails.append({
                "subject": subject,
                "sender": sender,
                "received_time": date_str,
                "body": body,
                "detected_language": language,
                "mapped_message_id": msg["id"]
            })
            print(f"✅ Processed: {subject} ({language})")
        except Exception as e:
            print(f"❌ Error processing thread: {e}")

    if not fetched_emails:
        print("⚠️ No valid emails found in inbox for the last 7 days.")
        return "No emails found in the last 7 days."

    # Step 3: Generate summaries
    for email in fetched_emails:
        body = email.get("body", "")
        language = email.get("detected_language", "English")
        email["summary"] = summarize_email_multilingual(body, language)

    # Step 4: Classify commands
    for email in fetched_emails:
        subject = email.get("subject", "")
        summary = email.get("summary", "")
        language = email.get("detected_language", "English")
        email["detected_commands"] = classify_multiple_commands(subject, summary, language)

    # Step 5: Generate reply drafts
    for email in fetched_emails:
        subject = email.get("subject", "")
        body = email.get("body", "")
        commands = email.get("detected_commands", [])
        language = email.get("detected_language", "English")

        draft1, draft2 = generate_reply_drafts(subject, body, commands, language)
        email["reply_draft_1"] = draft1
        email["reply_draft_2"] = draft2

    # Step 6: Analyze tone and confidence
    for email in fetched_emails:
        body = email.get("body", "")
        language = email.get("detected_language", "English")
        draft = email.get("reply_draft_1", "")
        commands = email.get("detected_commands", [])

        email["tone"] = detect_tone(body, language)
        email["reply_confidence"] = estimate_reply_confidence(draft, commands)

    # Step 7: Sync to Notion
    notion = NotionClient(auth=NOTION_TOKEN)
    
    successful_syncs = 0
    for email in fetched_emails:
        try:
            notion.pages.create(
                parent={"database_id": NOTION_DB_ID},
                properties={
                    "Email Subject": {
                        "title": [{"text": {"content": email.get("subject", "(No Subject)")[:200]}}]
                    },
                    "Sender Email": {
                        "email": email.get("sender", "")
                    },
                    "Date": {
                        "date": {
                            "start": email.get("received_time", datetime.utcnow().isoformat())
                        }
                    },
                    "Summary": {
                        "rich_text": [{"text": {"content": email.get("summary", "")[:2000]}}]
                    },
                    "Detected Commands": {
                        "rich_text": [{"text": {"content": ", ".join(email.get("detected_commands", []))}}]
                    },
                    "Tone": {
                        "select": {"name": email.get("tone", "unknown")}
                    },
                    "Language": {
                        "rich_text": [{"text": {"content": email.get("detected_language", "unknown")}}]
                    },
                    "Reply Draft 1": {
                        "rich_text": [{"text": {"content": email.get("reply_draft_1", "")[:2000]}}]
                    },
                    "Reply Draft 2": {
                        "rich_text": [{"text": {"content": email.get("reply_draft_2", "")[:2000]}}]
                    },
                    "Confidence Score": {
                        "number": email.get("reply_confidence", 0)
                    },
                    "Action Taken": {
                        "select": determine_action_taken(email)
                    },
                    "Team Tag": {
                        "multi_select": [{"name": tag} for tag in determine_team_tag(email.get("detected_commands", []))]
                    },
                    "Fallback Used": {
                        "checkbox": "[reply error" in email.get("reply_draft_1", "").lower()
                    },
                    "Status": {
                        "select": {"name": "Pending"}
                    }
                }
            )
            print(f"✅ Synced to Notion: {email['subject']}")
            successful_syncs += 1
        except Exception as e:
            print(f"❌ Error syncing '{email.get('subject', '')}': {str(e)}")

    # Return summary for Flask endpoint
    summary_message = f"""
📧 Gmail Assistant Processing Complete!

✅ Processed {len(fetched_emails)} emails from the last 7 days
✅ Generated summaries and classified commands
✅ Created reply drafts in multiple languages
✅ Analyzed tone and confidence scores
✅ Successfully synced {successful_syncs}/{len(fetched_emails)} emails to Notion

Languages detected: {', '.join(set(email.get('detected_language', 'Unknown') for email in fetched_emails))}
Most common commands: {', '.join(set().union(*[email.get('detected_commands', []) for email in fetched_emails]))}
    """.strip()

    print(summary_message)
    return summary_message


# For testing locally
if __name__ == "__main__":
    result = run_assistant()
    print("\n" + "="*50)
    print("FINAL RESULT:")
    print(result)
    