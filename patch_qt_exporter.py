import re
with open(r"c:\Users\Administrator\Desktop\Github Repos\vault-themes\qt_exporter.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix Inputs padding and borders
content = re.sub(r'padding: 5px 10px;\s*min-height: 30px;', r'padding: 2px 4px;\n                min-height: 22px;', content)
content = re.sub(r'border-radius: 7px;', r'border-radius: 3px;', content)

# Fix Buttons padding and borders
content = re.sub(r'padding: 7px 16px;\s*min-height: 30px;', r'padding: 3px 8px;\n                min-height: 22px;', content)
content = re.sub(r'border-radius: 8px;', r'border-radius: 4px;', content)

# Primary button radius
content = re.sub(r'border-radius: 10px;', r'border-radius: 4px;', content)

with open(r"c:\Users\Administrator\Desktop\Github Repos\vault-themes\qt_exporter.py", "w", encoding="utf-8") as f:
    f.write(content)
