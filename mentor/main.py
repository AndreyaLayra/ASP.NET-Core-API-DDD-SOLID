import os
import json
from github import Github
from openai import OpenAI, RateLimitError
from mentor.prompt import build_prompt
from mentor.rules import rule_based_review

MENTOR_COMMENT_HEADER = "🧠 **Tech Mentor Agent**"


def get_pull_request(github_client):
    repo_name = os.getenv("GITHUB_REPOSITORY")
    event_path = os.getenv("GITHUB_EVENT_PATH")

    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH not found")

    with open(event_path, "r", encoding="utf-8") as file:
        event_data = json.load(file)

    pr_number = event_data["pull_request"]["number"]
    repo = github_client.get_repo(repo_name)

    return repo.get_pull(pr_number)


def build_diff(pr, max_length=12000):
    diff = ""

    for file in pr.get_files():
        if file.patch:
            diff += f"\n--- {file.filename} ---\n{file.patch}\n"

        if len(diff) >= max_length:
            break

    return diff[:max_length]


def find_existing_mentor_comment(pr):
    for comment in pr.get_issue_comments():
        if comment.body.startswith(MENTOR_COMMENT_HEADER):
            return comment
    return None


def post_or_update_comment(pr, review_text):
    final_body = f"""{MENTOR_COMMENT_HEADER}

{review_text}

---
_Last updated automatically after new changes were pushed._
"""

    existing_comment = find_existing_mentor_comment(pr)

    if existing_comment:
        existing_comment.edit(final_body)
    else:
        pr.create_issue_comment(final_body)


def generate_review(openai_client, prompt, diff):
    rule_based_feedback = rule_based_review(diff)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a thoughtful senior technical mentor. "
                        "Complement the rule-based feedback below with deeper insights, "
                        "suggest improvements, and keep a supportive tone."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Rule-based analysis:\n{rule_based_feedback}\n\n"
                        f"Pull Request context:\n{prompt}"
                    )
                }
            ],
        )

        ai_feedback = response.choices[0].message.content.strip()

        return f"{rule_based_feedback}\n\n---\n\n🤖 **AI Mentor Insights**\n\n{ai_feedback}"

    except RateLimitError:
        return (
            f"{rule_based_feedback}\n\n---\n\n"
            "⚠️ **AI Mentor unavailable due to API quota limits**\n"
            "This review is based on static analysis rules only."
        )

def main():
    github_token = os.getenv("GITHUB_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is missing")

    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    github_client = Github(github_token)
    openai_client = OpenAI(api_key=openai_api_key)

    pr = get_pull_request(github_client)

    diff = build_diff(pr)

    prompt = build_prompt(
        pr_title=pr.title,
        pr_description=pr.body or "No description provided.",
        diff=diff,
    )

    review = generate_review(openai_client, prompt, diff)

    post_or_update_comment(pr, review)


if __name__ == "__main__":
    main()
