def get_mock_ocr(frame_path: str, timestamp: float) -> str:
    mock_data = {
        25.0: "Vector Addition: A + B = C",
        48.0: "C[i][j] = Σ A[i][k] * B[k][j]",
        70.0: "Algorithm Complexity Comparison\nBrute Force: O(n³)\nStrassen: O(n^2.807)\nCoppersmith-Winograd: O(n^2.376)",
        95.0: "Summary\n- Vectors\n- Matrices\n- Multiplication",
    }
    for ts, text in mock_data.items():
        if abs(ts - timestamp) < 10:
            return text
    return ""
