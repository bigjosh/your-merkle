# Purpose

A utility that helps you prove your pictures (or any files) are not AI generated in the future.

It generates a single 64-character hex string (the "tophash") that captures the state of all files in a directory tree. If you publish this tophash in a timestamped way, you can later prove that any specific file existed at that point in time.

# Definitions

- **tophash** - A 64-character hex string (256-bit hash) that captures the state of a set of files at a point in time.
- **snapshot** - A local file that stores all information needed to later build a proof for any file captured when the snapshot was created.
- **proof** - An ordered list of hash strings that allows anyone to verify a file is included in a tophash.

# Functionality

A Python console program with two commands:

1. **capture** - Compute a tophash and create a snapshot file for all files in the current directory tree
2. **prove** - Generate a proof for any file given a tophash and file path

# Usage

## Capture (lock in the state of your files)

```
cd /path/to/your/files
python your_merkle.py capture
```

This will:
1. Hash all non-hidden files in the directory tree
2. Create a snapshot file named `<tophash>.your-merkle.snapshot`
3. Print the tophash and file count

Publish the tophash in a timestamped way (tweet, opentimestamps.org, archive.org-indexed page, etc.).

## Prove (generate a proof for a file)

```
python your_merkle.py prove <tophash> <filepath>
```

Requirements:
- The snapshot file for the tophash must exist in the current directory
- The file must exist and be unchanged since capture

Outputs the proof chain as a list of hex strings.

## No-leak promise

A proof for one file reveals nothing about any other file's existence or contents.

Note: Anyone with access to the snapshot file can check if a file is captured, so keep the snapshot file private.

# Implementation Details

## Data Types

- All hashes are SHA-256 digests (256-bit), displayed as 64-character lowercase hex strings
- Unisalts are cryptographically random 256-bit values (one per file, stored in snapshot and included in proofs)
- Snapshot files store hashes and unisalts as 32-byte binary values

## Hash Combine Function

The combine function is **commutative** so proofs don't need left/right position information:

```python
def sha256_combine_commutative(h1: bytes, h2: bytes) -> bytes:
    hex1, hex2 = h1.hex(), h2.hex()
    a, b = (hex1, hex2) if hex1 <= hex2 else (hex2, hex1)
    combined = a + b  # concatenate sorted hex strings
    return hashlib.sha256(combined.encode('ascii')).digest()
```

Key points:
1. Convert both inputs to lowercase hex strings
2. Sort alphabetically (standard string comparison)
3. Concatenate (smaller first)
4. SHA-256 hash the concatenation as ASCII bytes



## Tree Construction (Capture)

Uses a stack-based approach with O(log N) space:

1. For each file:
   - Compute SHA-256 hash of file contents
   - Generate a random 256-bit unisalt
   - Write hash + unisalt to snapshot file (32 bytes each)
   - Combine hash and unisalt to create a leaf node
   - Merge with stack nodes of equal size until no equal-size node remains
2. Collapse remaining stack nodes to produce the final tophash

Hidden files (names starting with `.`) are skipped. Symlinks are followed.

## Snapshot File Format

- Filename: `<tophash>.your-merkle.snapshot`
- Contents: Sequence of 64-byte records (32-byte file hash + 32-byte unisalt)
- Order matches the order files were processed during capture, but this order is not significant for proof verification

## Proof Verification

See `check_proof.md` for standalone verification instructions.

A proof is a list of hash strings. To verify:
1. Start with `current = SHA256(file).hex()`
2. For each hash in the proof: `current = combine(current, hash)`
3. Check: `current == tophash`

## Requirements

- Python >= 3.11
- Uses `hashlib.file_digest()` for efficient file hashing
