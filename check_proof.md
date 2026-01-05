# Verifying a Proof

## Inputs

- **file**: The file you want to verify
- **tophash**: The published 256-bit hash 
- **proof**: An ordered list of 64-character lowercase hex strings

## Combine Function

To combine two hash strings `x` and `y`:

1. Sort them alphabetically (standard string comparison)
2. Concatenate them (smaller first): `sorted_concat = smaller + larger`
3. Hash the concatenation as ASCII text: `result = lowercase_hex(SHA256(sorted_concat))`

## Verification Algorithm

```
current = lowercase_hex(SHA256(file_contents))

for each hash_string in proof:
    current = combine(current, hash_string)

return current == tophash
```

## Example

```
current = "aaa111..."  (SHA256 of file)
proof   = ["bbb222...", "ccc333..."]
tophash = "ddd444..."

Step 1: combine("aaa111...", "bbb222...")
        -> sort: "aaa111..." < "bbb222..."
        -> concat: "aaa111...bbb222..."
        -> SHA256 of that string as ASCII bytes
        -> result: "xyz789..."

Step 2: combine("xyz789...", "ccc333...")
        -> sort: "ccc333..." < "xyz789..."
        -> concat: "ccc333...xyz789..."
        -> SHA256 of that string as ASCII bytes
        -> result: "ddd444..."

Verify: "ddd444..." == tophash 
```
