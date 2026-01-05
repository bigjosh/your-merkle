#!/usr/bin/env python3
"""
your-merkle: A utility to prove files existed at a point in time using Merkle trees.

Usage:
    python your_merkle.py capture
    python your_merkle.py prove <tophash> <filepath>
"""

import argparse
import hashlib
import os
import secrets
import shutil
import sys
import tempfile
from pathlib import Path
from typing import BinaryIO


SNAPSHOT_SUFFIX = ".your-merkle.snapshot"


def sha256_combine_commutative(h1: bytes, h2: bytes) -> bytes:
    """
    Combine two 32-byte SHA-256 digests commutatively.
    Converts to hex strings, concatenates in sorted order, then hashes.
    """
    if len(h1) != 32 or len(h2) != 32:
        raise ValueError("Inputs must be 32-byte SHA-256 digests")
    hex1, hex2 = h1.hex(), h2.hex()
    a, b = (hex1, hex2) if hex1 <= hex2 else (hex2, hex1)
    combined = a + b
    result = hashlib.sha256(combined.encode('ascii')).digest()
    return result


def hash_file(filepath: Path) -> bytes:
    """Compute SHA-256 hash of a file's contents."""
    with open(filepath, "rb") as f:
        return hashlib.file_digest(f, "sha256").digest()


def is_hidden(path: Path) -> bool:
    """Check if any component of the path is hidden (starts with '.')."""
    for part in path.parts:
        if part.startswith('.'):
            return True
    return False


def iter_files(root: Path):
    """
    Iterate over all non-hidden files in the directory tree.
    Follows symlinks. Yields Path objects.
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        # Filter out hidden directories in-place to prevent descending into them
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        
        for filename in filenames:
            if filename.startswith('.'):
                continue
            yield Path(dirpath) / filename


def capture(root: Path) -> None:
    """
    Capture the state of all files in the directory tree.
    Creates a snapshot file and prints the tophash.
    """
    # Stack for building the Merkle tree: list of (size, hash) tuples
    # size = number of leaves in the subtree
    stack: list[tuple[int, bytes]] = []
    file_count = 0
    
    # Create temp file for snapshot data
    temp_fd, temp_path = tempfile.mkstemp()
    try:
        with os.fdopen(temp_fd, "wb") as temp_file:
            for filepath in iter_files(root):
                # Compute file hash
                file_hash = hash_file(filepath)
                
                # Generate random unisalt
                unisalt = secrets.token_bytes(32)
                
                # Write hash and unisalt to temp file (32 bytes each, big-endian)
                temp_file.write(file_hash)
                temp_file.write(unisalt)
                
                # Combine hash and unisalt to create the leaf node
                node = sha256_combine_commutative(file_hash, unisalt)
                size = 1
                
                # Merge nodes of the same size
                while stack and stack[-1][0] == size:
                    _, sibling_hash = stack.pop()
                    node = sha256_combine_commutative(node, sibling_hash)
                    size *= 2
                
                stack.append((size, node))
                file_count += 1
                
                # Print status
                print(f"[{file_count}] {filepath}")
        
        if file_count == 0:
            raise Exception("no files captured")
        
        # Collapse remaining stack to get final tophash
        while len(stack) > 1:
            size1, node1 = stack.pop()
            size2, node2 = stack.pop()
            combined = sha256_combine_commutative(node1, node2)
            stack.append((size1 + size2, combined))
        
        total_files = stack[0][0]
        tophash = stack[0][1]
        tophash_hex = tophash.hex()
        
        # Move temp file to final location
        snapshot_filename = tophash_hex + SNAPSHOT_SUFFIX
        snapshot_path = root / snapshot_filename
        shutil.move(temp_path, snapshot_path)
        
        print()
        print(f"Snapshot file: {snapshot_filename}")
        print(f"Top hash: {tophash_hex}")
        print(f"Files captured: {total_files}")
        
    except:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def prove(tophash_hex: str, filepath: Path) -> None:
    """
    Generate a proof that a file is captured in a tophash.
    Prints the proof chain from file hash to tophash.
    """
    # Validate tophash format
    if len(tophash_hex) != 64:
        raise ValueError("tophash must be 64 hex characters")
    tophash = bytes.fromhex(tophash_hex)
    
    # Hash the target file
    if not filepath.exists():
        raise FileNotFoundError(f"file not found: {filepath}")
    
    target_hash = hash_file(filepath)
    
    # Open snapshot file
    snapshot_filename = tophash_hex + SNAPSHOT_SUFFIX
    if not os.path.exists(snapshot_filename):
        raise FileNotFoundError(f"snapshot file for specified tophash not found: {snapshot_filename}")
    
    # Read snapshot and rebuild the tree to find the proof path
    # We need to replay the tree construction and track the path for our target
    
    # Stack for building the Merkle tree: list of (size, hash, proof_chain or None) tuples
    # size = number of leaves in subtree, proof_chain tracks sibling hashes if subtree contains target
    stack: list[tuple[int, bytes, list[bytes] | None]] = []
    found_target = False
    target_unisalt: bytes | None = None
    
    with open(snapshot_filename, "rb") as f:
        while True:
            file_hash = f.read(32)
            if not file_hash:
                break
            unisalt = f.read(32)
            if len(unisalt) != 32:
                raise ValueError("Corrupt snapshot file")
            
            # Check if this is our target file
            is_target = (file_hash == target_hash)
            if is_target:
                found_target = True
                target_unisalt = unisalt
                # Start proof chain with unisalt (file_hash will be prepended at output)
                proof_chain: list[bytes] | None = [unisalt]
            else:
                proof_chain = None
            
            # Combine hash and unisalt to create the leaf node
            node = sha256_combine_commutative(file_hash, unisalt)
            size = 1
            
            # Merge nodes of the same size
            while stack and stack[-1][0] == size:
                _, sibling_hash, sibling_chain = stack.pop()
                
                # If either subtree contains our target, we need to track the sibling
                if proof_chain is not None:
                    proof_chain.append(sibling_hash)
                elif sibling_chain is not None:
                    proof_chain = sibling_chain
                    proof_chain.append(node)
                
                node = sha256_combine_commutative(node, sibling_hash)
                size *= 2
            
            stack.append((size, node, proof_chain))
    
    if not found_target:
        raise Exception(f"file hash not found in snapshot (file may have changed since capture)")
    
    # Collapse remaining stack
    while len(stack) > 1:
        _, node1, chain1 = stack.pop()
        _, node2, chain2 = stack.pop()
        
        # Merge proof chains
        if chain1 is not None:
            proof_chain = chain1
            proof_chain.append(node2)
        elif chain2 is not None:
            proof_chain = chain2
            proof_chain.append(node1)
        else:
            proof_chain = None
        
        combined = sha256_combine_commutative(node1, node2)
        stack.append((0, combined, proof_chain))  # size doesn't matter during final collapse
    
    final_hash = stack[0][1]
    final_chain = stack[0][2]
    
    # Verify we got the right tophash
    if final_hash != tophash:
        raise Exception("computed tophash does not match provided tophash (snapshot may be corrupt)")

    print(f"File hash: {target_hash.hex()}")
    print(f"Tophash  : {tophash_hex}")
    
    # Output the proof chain
    print(f"--- Start proof ---")
    for h in final_chain:
        print(h.hex())
    print("--- End proof ---")


def main():
    parser = argparse.ArgumentParser(
        description="Prove files existed at a point in time using Merkle trees."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # capture command
    capture_parser = subparsers.add_parser(
        "capture",
        help="Capture the state of all files in the current directory tree"
    )
    
    # prove command
    prove_parser = subparsers.add_parser(
        "prove",
        help="Generate a proof that a file is captured in a tophash"
    )
    prove_parser.add_argument("tophash", help="The 64-character hex tophash")
    prove_parser.add_argument("filepath", help="Path to the file to prove")
    
    args = parser.parse_args()
    
    if args.command == "capture":
        capture(Path.cwd())
    elif args.command == "prove":
        prove(args.tophash, Path(args.filepath))


if __name__ == "__main__":
    main()
