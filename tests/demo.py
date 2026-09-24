# ============================================================
# Markdown Cell 0
# ============================================================
# # 🚀 PaddleCLI CLI Test Notebook
# 
# This notebook demonstrates the streaming output capabilities of PaddleCLI CLI.

# ============================================================
# Cell 1
# ============================================================

# Cell 1: Basic print statements
print("Hello from PaddleCLI CLI!")
print("This is a streaming output test.")

for i in range(5):
    print(f"  Counting: {i+1}/5")

# ============================================================
# Cell 2
# ============================================================

# Cell 2: Import and data creation
import time
import numpy as np

print("Creating sample data...")
data = np.random.randn(100, 5)
print(f"Data shape: {data.shape}")
print(f"Data mean: {data.mean():.4f}")
print(f"Data std: {data.std():.4f}")

# ============================================================
# Cell 3
# ============================================================

# Cell 3: Progress simulation (streaming output)
print("Simulating a long-running process...")

for i in range(10):
    time.sleep(0.2)  # Simulate work
    progress = (i + 1) * 10
    bar = '█' * (i + 1) + '░' * (9 - i)
    print(f"\rProgress: [{bar}] {progress}%", end='', flush=True)

print("\n\n✅ Process complete!")

# ============================================================
# Cell 4
# ============================================================

# Cell 4: Using variables from previous cells
print("Using data from Cell 2...")
print(f"Data statistics:")
print(f"  Min: {data.min():.4f}")
print(f"  Max: {data.max():.4f}")
print(f"  Sum: {data.sum():.4f}")

# ============================================================
# Cell 5
# ============================================================

# Cell 5: Error handling test (this will fail)
print("This cell will produce an error...")
result = 1 / 0  # Division by zero
print("This line won't be reached")

# ============================================================
# Markdown Cell 6
# ============================================================
# ## Test Complete!
# 
# The notebook execution should have stopped at Cell 5 due to the error.
