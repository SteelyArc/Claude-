import base64, pathlib, sys
here = pathlib.Path(__file__).parent
font = pathlib.Path(sys.argv[1]).read_bytes()
src = (here / "sun.src.html").read_text()
(here / "sun.html").write_text(src.replace("__FONT__", base64.b64encode(font).decode()))
print("built sun.html")
