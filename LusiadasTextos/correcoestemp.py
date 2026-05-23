from __future__ import annotations

import argparse
from pathlib import Path


def process_text(text: str, stanza_size: int = 8) -> str:
	lines = text.splitlines()
	output: list[str] = []
	verse_count = 0
	lg_open = False

	def close_stanza() -> None:
		nonlocal lg_open, verse_count
		if lg_open:
			output.append("</lg>")
			lg_open = False
			verse_count = 0

	for line in lines:
		if line.startswith("<"):
			if lg_open:
				close_stanza()
			output.append(line)
			continue

		if not line.strip():
			if lg_open:
				close_stanza()
			output.append(line)
			continue

		if not lg_open:
			output.append('<lg type="estrofe">')
			lg_open = True

		output.append(f"<l>{line}</l>")
		verse_count += 1

		if verse_count == stanza_size:
			close_stanza()

	if lg_open:
		close_stanza()

	return "\n".join(output)


def main() -> None:
	parser = argparse.ArgumentParser(
		description=(
			"Envolve linhas de verso em <l> e agrupa estrofes em <lg type=\"estrofe\">."
		)
	)
	parser.add_argument("input_file", type=Path, help="Arquivo de entrada")
	parser.add_argument("output_file", type=Path, help="Arquivo de saída")
	parser.add_argument(
		"--stanza-size",
		type=int,
		default=8,
		help="Quantidade de linhas de verso por estrofe (padrão: 8)",
	)
	args = parser.parse_args()

	source_text = args.input_file.read_text(encoding="utf-8")
	result_text = process_text(source_text, stanza_size=args.stanza_size)
	args.output_file.write_text(result_text, encoding="utf-8")


if __name__ == "__main__":
	main()
