from pathlib import Path
import re

file_path = Path("c:/Users/bmaro/OneDrive/Documentos/LusiadasDigital/LusiadasTextos/LusiadasDireita.xml")
text = file_path.read_text(encoding="utf-8")

start = text.index('<div type="canto" n="5">')
end = text.index('</div>', start)
segment = text[start:end]
pattern = re.compile(r'(<lg type="estrofe" n=")(\d+)(">)')

active = False
counter = 51

def repl(match):
    global active, counter
    value = int(match.group(2))
    if not active:
        if value == 50:
            active = True
        return match.group(0)
    new_value = counter
    counter += 1
    return f'{match.group(1)}{new_value}{match.group(3)}'

new_segment = pattern.sub(repl, segment)
file_path.write_text(text[:start] + new_segment + text[end:], encoding="utf-8")

# validation
stanza_numbers = [int(m.group(1)) for m in re.finditer(r'<lg type="estrofe" n="(\d+)"', new_segment)]
print(stanza_numbers[:18])
print('has_duplicates', any(stanza_numbers.count(n) > 1 for n in stanza_numbers))
print('first_block', stanza_numbers[5:20])
