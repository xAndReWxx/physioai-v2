import numpy as np

def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    Calculate angle between three points.
    b is the vertex.
    Returns angle in degrees.
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    ba = a - b
    bc = c - b
    
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    
    return float(np.degrees(angle))

def calculate_angle_2d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Calculate 2D angle (xy plane only)."""
    return calculate_angle(a[:2], b[:2], c[:2])

def get_vertical_angle(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate angle of the line ab relative to vertical y-axis.
    Useful for forward head (ear relative to shoulder vertically).
    """
    a = np.array(a[:2])
    b = np.array(b[:2])
    
    # Vertical line going down from b
    vertical_pt = np.array([b[0], b[1] + 1.0])
    
    return calculate_angle_2d(a, b, vertical_pt)
