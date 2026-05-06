from pathlib import Path

p = Path('main.py')
s = p.read_text(encoding='utf-8')

old = 'À-ÖØ-öø-ÿ'
new = 'À-ÖØ-öø-ÿçğıöşüÇĞİÖŞÜ'
s = s.replace(old, new)

p.write_text(s, encoding='utf-8')
print('Turkish subtitle letters preserved')
