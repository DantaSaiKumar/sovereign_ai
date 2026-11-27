import ast, hashlib, re
from pathlib import Path
from .config import UPLOAD_DIR, MAX_UPLOAD_MB

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".csv", ".xlsx", ".png", ".jpg", ".jpeg", ".webp"}

def safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name[:120] or "upload"

def validate_upload(name: str, size: int):
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext or '(no extension)'}")
    if size <= 0:
        raise ValueError("Empty files are not accepted.")
    if size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"File exceeds the {MAX_UPLOAD_MB} MB upload limit.")
    return ext

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)

def safe_calculate(expression: str):
    """Evaluate arithmetic only. No names, calls, attributes, imports, or indexing."""
    if len(expression) > 160:
        raise ValueError("Expression is too long.")
    tree = ast.parse(expression, mode="eval")
    def walk(node, depth=0):
        if depth > 20:
            raise ValueError("Expression is too complex.")
        if isinstance(node, ast.Expression):
            return walk(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 10**12:
                raise ValueError("Numeric literal is too large.")
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
            left, right = walk(node.left, depth + 1), walk(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and abs(right) > 8:
                raise ValueError("Exponent is limited to 8.")
            value = {
                ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                ast.Mult: lambda: left * right, ast.Div: lambda: left / right,
                ast.FloorDiv: lambda: left // right, ast.Mod: lambda: left % right,
                ast.Pow: lambda: left ** right
            }[type(node.op)]()
            if abs(value) > 10**15:
                raise ValueError("Result is too large.")
            return value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
            value = walk(node.operand, depth + 1)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError("Only basic arithmetic is permitted.")
    return walk(tree)
