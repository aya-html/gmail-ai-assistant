#!/usr/bin/env python
# coding: utf-8

# 📥 Unified Gmail Assistant – DWDA (Domain-Wide Delegation) Ready
# Wrapped in run_assistant() for Flask & Cloud Run deployment
# Fixed for latest OpenAI client compatibility

def run_assistant():
    """
    Main function that runs the complete Gmail processing pipeline.
    Returns a summary string for Flask endpoint.
    """
    import os
    import sys
    import google.auth
    from googleapiclient.discovery import build
    from base64 import urlsafe_b64decode
    from datetime import datetime, timedelta
    from dotenv import load_dotenv
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

    # === Configure OpenAI client (FIXED VERSION) ===
    try:
        # Import and initialize OpenAI client correctly
        from openai import OpenAI
        
        # Initialize with ONLY the API key - no other parameters
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Test the connection with a simple call
        test_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("✅ OpenAI API connection verified successfully")
        
    except Exception as e:
        print(f"❌ OpenAI initialization error: {str(e)}")
        raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")

    # === Gmail API Setup (DWDA) ===
    try:
        SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
        creds, project_id = google.auth.default(scopes=SCOPES)
        service = build("gmail", "v1", credentials=creds)
        print(f"✅ Gmail API authenticated via DWDA service account (Project: {project_id})")
    except Exception as e:
        print(f"❌ Gmail API authentication error: {str(e)}")
        raise ValueError(f"Failed to authenticate with Gmail API: {str(e)}")

    # === Helper Functions ===
    def extract_text_from_parts(parts):
        """Extract text content from Gmail message parts"""
        if not parts:
            return ""
            
        for part in parts:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    try:
                        return urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    except Exception:
                        continue
            elif mime_type == "multipart/alternative" and "parts" in part:
                result = extract_text_from_parts(part["parts"])
                if result:
                    return result
            elif "parts" in part:
                result = extract_text_from_parts(part["parts"])
                if result:
                    return result
        return ""

    def safe_openai_call(prompt, model="gpt-3.5-turbo", max_tokens=300, temperature=0.4):
        """Safe wrapper for OpenAI API calls with error handling"""
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ OpenAI API call failed: {str(e)}")
            return f"[API Error: {str(e)}]"

    def detect_language(text):
        """Detect the language of email content using OpenAI"""
        if not text or len(text.strip()) < 10:
            return "English"
            
        prompt = f"What language is this email written in? Reply with only the language name.\n\nText: {text[:500]}"
        result = safe_openai_call(prompt, max_tokens=10, temperature=0)
        
        # Fallback to English if API error
        if result.startswith("[API Error"):
            return "English"
        return result

    def summarize_email_multilingual(body, language):
        """Generate multilingual summary of email content"""
        if not body or len(body.strip()) < 20:
            return "Email contains no meaningful content to summarize."
            
        prompt = f"""You are a smart assistant. Summarize the email below in a clear, short paragraph (3–5 lines) for a team inbox dashboard.

Write the summary in this language: **{language}**

EMAIL:
---
{body[:1500]}
---
SUMMARY:"""
        
        result = safe_openai_call(prompt, model="gpt-3.5-turbo", max_tokens=200, temperature=0.4)
        
        # Return fallback if API error
        if result.startswith("[API Error"):
            return f"Email from sender regarding {body[:100]}..." if body else "No content available"
        return result

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
        if not subject and not summary:
            return ["no_action"]
            
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
        
        result = safe_openai_call(prompt, model="gpt-3.5-turbo", max_tokens=100, temperature=0.3)
        
        # Parse the result safely
        try:
            if result.startswith("[API Error"):
                return ["no_action"]
                
            # Try to evaluate as Python list
            if result.startswith("[") and result.endswith("]"):
                commands = eval(result)
                return [cmd for cmd in commands if cmd in COMMAND_LIST] or ["no_action"]
            else:
                return ["no_action"]
        except Exception:
            return ["no_action"]

    def generate_reply_drafts(subject, body, commands, language):
        """Generate two versions of email replies"""
        if not commands or "no_action" in commands:
            return "[Skipped – Not a business-relevant message]", "[Skipped – Not a business-relevant message]"

        if not body or len(body.strip()) < 10:
            return "[Skipped – No meaningful content]", "[Skipped – No meaningful content]"

        prompt_common = f"""
You are a professional email assistant representing a modern company.
Your job is to write helpful, human-readable, thoughtful replies based on the user's original message.

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
{body[:1000]}
---

Guidelines:
- Write in the same language as the email ({language}).
- Cover all user requests naturally (if more than one).
- Avoid copying the user's email content.
- Be warm but professional. Clear and to-the-point.
- Keep each reply around 3–6 sentences.
- Close with a relevant polite sign-off.
"""

        # Generate both versions
        prompt_v1 = prompt_common + "\nTone: Professional and clear.\n\nReply:"
        prompt_v2 = prompt_common + "\nTone: Friendly and supportive.\n\nReply:"

        draft1 = safe_openai_call(prompt_v1, model="gpt-3.5-turbo", max_tokens=400, temperature=0.4)
        draft2 = safe_openai_call(prompt_v2, model="gpt-3.5-turbo", max_tokens=400, temperature=0.6)

        return draft1, draft2

    def detect_tone(body, language="English"):
        """Detect emotional tone of email"""
        if not body or len(body.strip()) < 10:
            return "neutral"
            
        prompt = f"""
You are a tone analysis expert.

Please classify the emotional tone of the following email in one word:
Choose only from: positive, neutral, negative, mixed

Language: {language}

EMAIL:
---
{body[:500]}
---

TONE:"""
        
        result = safe_openai_call(prompt, max_tokens=10, temperature=0.3)
        
        # Validate result
        valid_tones = ["positive", "neutral", "negative", "mixed"]
        tone = result.lower().strip()
        return tone if tone in valid_tones else "neutral"

    def estimate_reply_confidence(draft, commands):
        """Estimate confidence score for reply quality"""
        if not draft or "[skip" in draft.lower() or "[api error" in draft.lower():
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
        draft1 = email.get("reply_draft_1", "").lower()
        if "[skip" in draft1:
            return {"name": "Skipped", "color": "gray"}
        if "[api error" in draft1:
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
            elif cmd in ["job_application", "cv_update_request"]:
                tags.append("HR")
            elif cmd in ["contract_request", "legal_inquiry"]:
                tags.append("Legal")
            elif cmd in ["shipping_issue", "inventory_request"]:
                tags.append("Ops")
        return list(set(tags)) or ["General"]

    # === Main Processing Pipeline ===
    
    print("🚀 Starting Gmail Assistant processing...")
    
    # Step 1: Fetch emails from last 7 days
    try:
        now = datetime.utcnow()
        past = (now - timedelta(days=7)).strftime('%Y/%m/%d')
        query = f"after:{past} in:inbox"

        print(f"📬 Searching for emails after {past}...")
        
        threads_result = service.users().threads().list(
            userId='me', 
            q=query, 
            maxResults=25  # Reduced for faster processing
        ).execute()
        
        threads = threads_result.get('threads', [])
        print(f"📬 Found {len(threads)} email threads to process...")
        
        if not threads:
            print("⚠️ No emails found in the last 7 days.")
            return "✅ No new emails found in the last 7 days. Inbox is up to date!"

    except Exception as e:
        print(f"❌ Error fetching emails: {str(e)}")
        raise ValueError(f"Failed to fetch emails from Gmail: {str(e)}")

    # Step 2: Process each thread
    fetched_emails = []
    processed_count = 0
    
    for i, thread in enumerate(threads, 1):
        try:
            print(f"📧 Processing email {i}/{len(threads)}...")
            
            # Get the message
            msg = service.users().messages().get(userId='me', id=thread['id']).execute()
            payload = msg.get('payload', {})
            headers = {h['name']: h['value'] for h in payload.get('headers', [])}

            # Extract basic info
            subject = headers.get("Subject", "(No Subject)")[:200]  # Limit length
            sender = headers.get("From", "")[:100]  # Limit length
            
            # Parse timestamp
            timestamp = int(msg.get("internalDate", 0)) / 1000
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            # Extract body text
            body = extract_text_from_parts(payload.get("parts", []))
            if not body:
                # Try getting from payload body directly
                body_data = payload.get("body", {}).get("data")
                if body_data:
                    try:
                        body = urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
                    except:
                        body = "[No readable content]"
                else:
                    body = "[No text content found]"

            # Skip if body is too short or looks like spam
            if len(body.strip()) < 20:
                print(f"⏭️ Skipped (too short): {subject}")
                continue

            # Detect language
            language = detect_language(body)

            fetched_emails.append({
                "subject": subject,
                "sender": sender,
                "received_time": date_str,
                "body": body[:2000],  # Limit body length
                "detected_language": language,
                "mapped_message_id": msg["id"]
            })
            
            processed_count += 1
            print(f"✅ Processed: {subject[:50]}... ({language})")
            
        except Exception as e:
            print(f"❌ Error processing thread {i}: {str(e)}")
            continue

    if not fetched_emails:
        print("⚠️ No valid emails were processed successfully.")
        return "⚠️ Found emails but could not process any successfully. Check logs for details."

    print(f"📊 Successfully processed {processed_count} emails. Starting AI analysis...")

    # Step 3: Generate summaries
    for i, email in enumerate(fetched_emails, 1):
        print(f"🧠 Generating summary {i}/{len(fetched_emails)}...")
        body = email.get("body", "")
        language = email.get("detected_language", "English")
        email["summary"] = summarize_email_multilingual(body, language)

    # Step 4: Classify commands
    for i, email in enumerate(fetched_emails, 1):
        print(f"🎯 Classifying commands {i}/{len(fetched_emails)}...")
        subject = email.get("subject", "")
        summary = email.get("summary", "")
        language = email.get("detected_language", "English")
        email["detected_commands"] = classify_multiple_commands(subject, summary, language)

    # Step 5: Generate reply drafts
    for i, email in enumerate(fetched_emails, 1):
        print(f"✍️ Generating replies {i}/{len(fetched_emails)}...")
        subject = email.get("subject", "")
        body = email.get("body", "")
        commands = email.get("detected_commands", [])
        language = email.get("detected_language", "English")

        draft1, draft2 = generate_reply_drafts(subject, body, commands, language)
        email["reply_draft_1"] = draft1
        email["reply_draft_2"] = draft2

    # Step 6: Analyze tone and confidence
    for i, email in enumerate(fetched_emails, 1):
        print(f"📈 Analyzing tone {i}/{len(fetched_emails)}...")
        body = email.get("body", "")
        language = email.get("detected_language", "English")
        draft = email.get("reply_draft_1", "")
        commands = email.get("detected_commands", [])

        email["tone"] = detect_tone(body, language)
        email["reply_confidence"] = estimate_reply_confidence(draft, commands)

    # Step 7: Sync to Notion
    print("🔄 Syncing to Notion database...")
    try:
        notion = NotionClient(auth=NOTION_TOKEN)
        successful_syncs = 0
        
        for i, email in enumerate(fetched_emails, 1):
            try:
                print(f"💾 Syncing to Notion {i}/{len(fetched_emails)}...")
                
                # Create the page
                notion.pages.create(
                    parent={"database_id": NOTION_DB_ID},
                    properties={
                        "Email Subject": {
                            "title": [{"text": {"content": email.get("subject", "(No Subject)")[:100]}}]
                        },
                        "Sender Email": {
                            "email": email.get("sender", "")[:100] if "@" in email.get("sender", "") else None
                        },
                        "Date": {
                            "date": {
                                "start": email.get("received_time", datetime.utcnow().isoformat())[:19]
                            }
                        },
                        "Summary": {
                            "rich_text": [{"text": {"content": email.get("summary", "")[:2000]}}]
                        },
                        "Detected Commands": {
                            "rich_text": [{"text": {"content": ", ".join(email.get("detected_commands", []))}}]
                        },
                        "Tone": {
                            "select": {"name": email.get("tone", "neutral")}
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
                            "number": min(100, max(0, email.get("reply_confidence", 0)))
                        },
                        "Action Taken": {
                            "select": determine_action_taken(email)
                        },
                        "Team Tag": {
                            "multi_select": [{"name": tag} for tag in determine_team_tag(email.get("detected_commands", []))]
                        },
                        "Status": {
                            "select": {"name": "Pending"}
                        }
                    }
                )
                successful_syncs += 1
                print(f"✅ Synced: {email['subject'][:50]}...")
                
            except Exception as e:
                print(f"❌ Error syncing '{email.get('subject', '')[:50]}': {str(e)}")
                continue

    except Exception as e:
        print(f"❌ Notion connection error: {str(e)}")
        return f"⚠️ Processed {len(fetched_emails)} emails but failed to sync to Notion: {str(e)}"

    # Generate summary statistics
    languages = set(email.get('detected_language', 'Unknown') for email in fetched_emails)
    all_commands = []
    for email in fetched_emails:
        all_commands.extend(email.get('detected_commands', []))
    
    common_commands = list(set(all_commands))[:5]  # Top 5 unique commands

    # Return comprehensive summary for Flask endpoint
    summary_message = f"""
📧 Gmail Assistant Processing Complete! ✅

📊 PROCESSING SUMMARY:
• Processed: {len(fetched_emails)} emails from the last 7 days
• Notion Sync: {successful_syncs}/{len(fetched_emails)} successful
• Languages: {', '.join(sorted(languages)) if languages else 'None detected'}
• Commands: {', '.join(common_commands) if common_commands else 'None detected'}

🤖 AI ANALYSIS COMPLETED:
• Email summaries generated
• Commands classified  
• Reply drafts created (2 versions each)
• Tone analysis performed
• Confidence scores calculated

🎯 NEXT STEPS:
• Check your Notion database for all processed emails
• Review reply drafts and send when ready
• Monitor team tags for proper routing

⚡ All done! Your inbox is now AI-processed and organized.
    """.strip()

    print("\n" + "="*50)
    print("GMAIL ASSISTANT COMPLETED SUCCESSFULLY!")
    print("="*50)
    print(summary_message)
    return summary_message


# For testing locally
if __name__ == "__main__":
    try:
        result = run_assistant()
        print("\n" + "="*50)
        print("FINAL RESULT:")
        print(result)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
