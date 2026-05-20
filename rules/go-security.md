---
description: Go-specific security idioms — stdlib functions and patterns. The general signal table lives in owasp-top-10.md.
paths:
  - "**/*.go"
---

# Go Security Idioms

> See `owasp-top-10.md` for the general signal table and mandatory behaviors. This file lists the Go-specific *how*.

## SQL — parameterized queries

Use the driver's placeholder (`$1` for pgx/lib-pq, `?` for mysql/sqlite). Never `fmt.Sprintf` or `+` to build SQL.

```go
row := db.QueryRowContext(ctx, "SELECT * FROM users WHERE email = $1", email)
```

## Subprocess — argument list, never `sh -c`

```go
exec.Command("grep", "--", userInput, filename)   // no shell
```

Use `--` to terminate flag parsing before any user-supplied positional argument.

## Path traversal — confine to base

```go
clean := filepath.Clean(filepath.Join(baseDir, userPath))
if !strings.HasPrefix(clean, baseDir+string(os.PathSeparator)) {
    return errors.New("path traversal")
}
```

## CSPRNG — `crypto/rand`, never `math/rand`

```go
b := make([]byte, 32)
_, err := cryptorand.Read(b)
```

For tokens, take bytes from `crypto/rand` and base64-encode.

## Constant-time comparison — `hmac.Equal`

Never `==` or `bytes.Equal` on secrets, signatures, or HMACs.

## TLS — `MinVersion: tls.VersionTLS12`, verification on

Never `InsecureSkipVerify: true` outside explicit local test fixtures. If a cert chain fails, fix the chain.

## Outbound HTTP — block redirect chains when not needed

```go
&http.Client{CheckRedirect: func(*http.Request, []*http.Request) error {
    return http.ErrUseLastResponse
}}
```

Prevents the redirect-after-allowlist pivot to internal hosts.

## Request body bounds — `http.MaxBytesReader`

```go
r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // 1 MiB cap
```

## Password hashing — `golang.org/x/crypto/bcrypt`

`bcrypt.GenerateFromPassword` / `bcrypt.CompareHashAndPassword`. Never `crypto/sha256` for passwords.
