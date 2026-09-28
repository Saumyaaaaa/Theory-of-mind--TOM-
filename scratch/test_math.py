import re

text = "A very common choice people use is the letter $x$ or the letter $n$ to stand in for that missing amount. If you had $6, and added $x$, you get $x + 6$. Also $y = 3x - 1$."

# Regex for inline math: $var$ or $expression$ where inside has at least one letter and no nested $ or newlines
pattern = re.compile(r"(\$(?!\s)[^$\n]*?[a-zA-Z][^$\n]*?(?<!\s)\$)")

parts = pattern.split(text)
print("Parts count:", len(parts))
for part in parts:
    if part.startswith("$") and part.endswith("$") and len(part) >= 3:
        inner = part[1:-1].strip()
        print("MATH:", repr(inner))
    else:
        print("TEXT:", repr(part))
