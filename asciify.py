
import sys
from pathlib import Path
import unicodedata

# Translate the following unicode characters as follows:
TRANSLATIONS = str.maketrans({
    "—": "--",
    "–": "-",
    "−": "-",
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
    "×": "x",
    "°": "deg",
})

def main(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    # Apply the translation table above
    text = text.translate(TRANSLATIONS)

    # Change characters with accents to accentless for now
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(
        ch for ch in text
        if not unicodedata.combining(ch)
    )
    text = text.encode('ascii', 'ignore').decode('ascii')

    path.write_text("".join(text), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} FILE.rst")
        sys.exit(1)
    main(sys.argv[1])
