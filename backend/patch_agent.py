import re

with open("backend/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the tools array if it's missing tool_search_policy
if "tool_search_policy" not in content:
    content = content.replace("    tools = [", """    def tool_search_policy(query: str) -> str:
        \"\"\"Search the internal Paytm knowledge base and policy rules.\"\"\"
        from backend.rag import search_policy
        res = search_policy(query)
        log_func("INVESTIGATION", "search_policy", "SUCCESS", f"AI queried policy KB: {query}")
        return res

    tools = [""")
    content = content.replace("tool_check_settlement\n    ]", "tool_check_settlement,\n        tool_search_policy\n    ]")

# Fix the prompt
old_prompt = r"Your task:.*?(?=Be precise and factual)"
new_prompt = """Your task:
1. Use your tools to check the status of this transaction across all 4 systems (Bank, Network, Merchant, Settlement). You must call all 4 tools.
2. Use the `tool_search_policy` tool to look up the relevant rule or SLA based on what you find.
3. Once you have all the results and policy context, write a concise investigation summary in exactly 3-4 sentences that:
   - States what happened to the customer's money based on the bank status.
   - Identifies the specific discrepancy found across the four payment systems.
   - States the exact policy rule that applies to this situation based on your policy search.

"""
content = re.sub(old_prompt, new_prompt, content, flags=re.DOTALL)

with open("backend/agent.py", "w", encoding="utf-8") as f:
    f.write(content)
