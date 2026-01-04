# purpose
A utility that will help you prove your pitcutres not AI generated in the future.

It does this by generating a single 16 letter long string that can later be used to prove any file in a directory tree existed when the string was generated. If you publish this string in some timestamped way, then you can later prove that the files existed at that point in time.

# definitions

`tophash` - a 64 character long string that captures the state of a directory tree at a point in time. 
`snapshot` - a local file that saves all of the information about a directory tree that would be needed later to build a proof for any one of the files in that tree.

# functionality

A python console program with two  releated functions:
1. capture- compute a tophash plus create a snapshot file of all the files in a directory tree 
2. prove- build a proof for any one of the files in that tree given a tophash and a file path

# use

## do this now to lock in the state of your files

1. Run the program with the `capture` command to compute the tophash of all the files in a full directory tree. 
2. Publish the resulting tophash in some timestamped way so you can later prove that it existed at a point in time. Could be in a tweet, or via opentimestamps.org, or a website that is indexed by archive.org.
3. Keep the generated snapshot file in the directory tree- you will need it later if you ever want to generate a proof for any of the files captured in that tophash/snapshot.

## later to prove a file is captured in a tophash

1. run the program with the `prove` command in the same directory as when you captured the files and provide (1) a tophash and (2) the path to the file you want to prove.
2. If the following are both true:
    1. there is a snapshot file in the directory that matches the supplied tophash
    2. the file exists in the directory tree and it hash not changed since the snapshot was created
then the program will produce a proof showing that the file was, in fact, captured in the tophash. 

## no-leak promise

We guarantee that the proof for any one file's existsance does not reveal any information about any other file's existsance or contents.

Do note, however, that anyone with access to the snapshot file can check to see if a file is captured in the tophash for that snapshot, so keep that private.

# implementation details

# data types

all hashes are sha256 hash digests and are 256-bit integers. They are converted to ascii hex strings when shown to the user.

all unisalts are crytogaphically random 256-bit integers. These are not shown to the user and they only appear in the snapshot file or in a proof.

when hashes or unisalts are stored in a snapshot file, they are stored as 32-byte integers in big-endian byte order.

when hashes or unisalts are processed in memory, they are stored as `bytes` objects of length 32 to be directly compatible with the return value of the `sha256().digest()` function.

# hash combine function

```
import hashlib

def sha256_combine_commutative(h1: bytes, h2: bytes) -> bytes:
    """
    h1, h2: 32-byte SHA-256 digests (as returned by hashlib.sha256(...).digest()).
    Returns: 32-byte digest of SHA256(sorted(h1,h2) concatenated).
    """
    if len(h1) != 32 or len(h2) != 32:
        raise ValueError("Inputs must be 32-byte SHA-256 digests")
    a, b = (h1, h2) if h1 <= h2 else (h2, h1)
    return hashlib.sha256(a + b).digest()
```

It is important that it be communitive so that a proof can consist of only a list of hashes without needing any left/right information.



# Tree construction details for capture

The tree is built by processing files sequentially and using a stack-based approach where each level of the stack represents a pending node at that height. This ensures O(log N) space usage during capture while maintaining the correct Merkle tree structure.

The algorithm works as follows:
1. For each file, compute its hash and combine it with a random unisalt
2. Push the resulting node onto a stack
3. While the stack has at least two nodes at the same height, pop them, combine them using the commutative hash function, and push the result back
4. The final top hash is the root of the Merkle tree


# Proof construction 

A proof is constructed starting with the computed file hash. We then iterate through the snapshot file to find the file hash and output the necessary sibling hashes along the way to reconstruct the path to the root.

# Snapshot file format

The filename of a snapshot file is the tophash in hex form + ".your-merkle.snapshot".

The file contains one pair of 32-byte integers in big-endian byte order for each file captured. The first integer is the hash of the file contents. The second integer is the unisalt for that file.

Note that the order of the files in the snapshot file is not specified (but in practice it should be the same as the order in which they were captured).

# capture process

1. create a temp file
2. recusively iterate though all files in the directory tree
    1. init hash_value to empty and a total file counter to zero
    2. for each file, compute the hash and also generate a random unisalt value
    3. append the hash and unisalt values to the end of the temp file as 32 bytes each in big-endian byte order
    4. use the above tree construction algorithm to combine the hash and unisalt into a file node
    3. increment a total file counter
    7. print a status message showing the total file count and file name
3. check if the hash_value is empty, and if so, raise a "no files captured" exception
4. close the temp file and move it to the current directory with a name composed of the computed top hash in hex form + “.your-merkle.snapshot”.
5. print a final status message to the console showing the name of the new snapshot file and the computed top hash.

# proof process

1. attempt to open the file at the path specified by the user. if the file does not exist, raise a "file not found" exception.
2. generate the hash of the file contents.
3. attempt to open the snapshot file with the name composed of the supplied top hash in hex form + “.your-merkle.snapshot”. if the file does not exist, raise a "snapshot file for specified tophash not found" exception.
4. iterate though the snapshot file, reading the hash and unisalt values for each file. Use the proof construction algorithm to build and print the chain of hashes from the file hash to the top hash.

# Details
Assume python >= 3.11 and use `hashlib.file_digest()`.

Do not catch exceptions unless explicitly called for above. Let them percolate up to the console so the user can see them.

There may be millions of files, so do not try to keep everything in memory. Work iteratively instead

Favor a simple, clear, and human legible coding style. Comment whenever it is not obvious what is happening or how.

Use type hints and type annotations where appropriate.
