import os
import json
from github import Github
from openai import OpenAI
from mentor.prompt import build_prompt
 
MENTOR_COMMENT_HEADER = "🧠 **Tech Mentor Agent**"

def get_pull_request(github_client):
    repo_name = os.getenv("GITHUB_REPOSITORY")
    event_path = os.getenv("GITHUB_EVENT_PATH")

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


def generate_review(openai_client, prompt):
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": "You are a thoughtful senior technical mentor."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
    )

    return response.choices[0].message.content.strip()


def main():
    github_token = os.getenv("GITHUB_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not github_token or not openai_api_key:
        raise RuntimeError("Missing required environment variables.")

    github_client = Github(github_token)
    openai_client = OpenAI(api_key=openai_api_key)

    pr = get_pull_request(github_client)

    diff = build_diff(pr)

    prompt = build_prompt(
        pr_title=pr.title,
        pr_description=pr.body or "No description provided.",
        diff=diff
    )

    review = generate_review(openai_client, prompt)

    post_or_update_comment(pr, review)


if __name__ == "__main__":
    main()