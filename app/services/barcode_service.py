import uuid


def generate_barcode(book_id, student_id, barcode_exists=None, max_attempts=5):
    for _ in range(max_attempts):
        candidate = f"TXN-{book_id}-{student_id}-{uuid.uuid4().hex}"
        if barcode_exists is None or not barcode_exists(candidate):
            return candidate

    raise RuntimeError("Unable to generate a unique barcode.")
