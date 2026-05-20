---
description: Go concurrency patterns — channels, select, worker pools, context, leak prevention.
paths:
  - "**/*.go"
---

# Go Concurrency

## Principles

- Do not communicate by sharing memory; share memory by communicating
- Distinguish concurrency (structuring as independent components) from parallelism (multi-CPU execution)
- Always pass `context.Context` as the first parameter on any function that does I/O or blocks
- Use `errgroup` for concurrent work with error propagation
- Channels should have a clear owner — one goroutine creates, one closes; close in the sender, never the receiver
- Prevent goroutine leaks: every goroutine must have a termination path (quit channel, `done` channel, or context)
- Start goroutines when you have concurrent work to do; exit them as soon as the work is done

## Generator pattern

- Return `<-chan T` (receive-only) from a function that launches a goroutine internally — callers iterate with `for v := range ch`
- The goroutine that creates the channel owns it and is responsible for `close(ch)` when done
- Pair every generator with a quit/done signal so callers can stop it early without leaking the producer goroutine

```go
func generate(done <-chan struct{}, values ...int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for _, v := range values {
            select {
            case out <- v:
            case <-done:
                return
            }
        }
    }()
    return out
}
```

## Fan-in (multiplexer)

- Merge multiple input channels into one output channel by spawning one forwarding goroutine per input
- Use `sync.WaitGroup` to close the output channel only after all forwarders finish

```go
func merge(done <-chan struct{}, cs ...<-chan int) <-chan int {
    var wg sync.WaitGroup
    out := make(chan int)
    forward := func(c <-chan int) {
        defer wg.Done()
        for v := range c {
            select {
            case out <- v:
            case <-done:
                return
            }
        }
    }
    wg.Add(len(cs))
    for _, c := range cs { go forward(c) }
    go func() { wg.Wait(); close(out) }()
    return out
}
```

## Select patterns

- Enable/disable a `select` case by toggling the channel variable: set to `nil` to disable, set to the real channel to re-enable
- Use this to suppress sends when there is nothing pending, preventing spurious blocking

```go
var out chan Item   // nil — send case is disabled
if len(pending) > 0 {
    out = realOut  // enable the send case
}
select {
case out <- pending[0]:
    pending = pending[1:]
case item := <-in:
    pending = append(pending, item)
}
```

- For a **whole-operation timeout**, call `time.After` once outside the loop; calling it inside the loop creates a new timer each iteration and the deadline never triggers
- For a **per-message timeout**, call `time.After` inside the loop

```go
// global deadline — call ONCE outside the loop
timeout := time.After(5 * time.Second)
for {
    select {
    case msg := <-c:
        // handle
    case <-timeout:
        return
    }
}
```

- Use `select` with `default` for non-blocking channel operations (try-send / try-receive)

## Quit signal with cleanup

- Pass a `quit` channel to a goroutine; include a `select` case on it alongside normal work
- For confirmed shutdown with cleanup: use the same channel bidirectionally — caller sends stop signal, goroutine sends acknowledgement after cleanup

```go
select {
case c <- value:
case <-quit:
    cleanup()
    quit <- struct{}{} // ack
    return
}
```

## Scatter-gather and replicated requests

- Run concurrent operations by launching one goroutine per task; collect results with a channel
- Always use a **buffered channel** sized to the number of senders so abandoned goroutines (timed out) can send and exit without leaking

```go
c := make(chan Result, len(replicas)) // buffered — not unbuffered
for _, r := range replicas {
    go func(r Search) { c <- r(query) }(r)
}
return <-c // take first; others send into buffer and exit cleanly
```

## Worker pool

- Cap concurrency with a fixed pool of N workers reading from a shared `jobs` channel
- `close(jobs)` signals all workers to exit after draining (`for j := range jobs` terminates on close)
- Use `sync.WaitGroup` + a closing goroutine to close the `results` channel only after all workers finish

```go
func worker(jobs <-chan int, results chan<- int, wg *sync.WaitGroup) {
    defer wg.Done()
    for j := range jobs { results <- process(j) }
}

jobs := make(chan int, 100)
results := make(chan int, 100)
var wg sync.WaitGroup
for i := 0; i < numWorkers; i++ { wg.Add(1); go worker(jobs, results, &wg) }
go func() { wg.Wait(); close(results) }()
```

## Bounded parallelism with cancellation

- Use a `done <-chan struct{}` to propagate cancellation to both a feeder (walker) and all workers
- Workers check `done` in their `select` to exit early on cancellation
- The feeder uses a buffered error channel (`errc := make(chan error, 1)`) so it never blocks on error send

## Context

- Use `context.Context` (not a raw `done` channel) for cancellation in HTTP handlers and any code that crosses service/API boundaries
- Always `defer cancel()` immediately after `context.WithCancel` / `WithTimeout` / `WithDeadline` — failing to call `cancel` leaks the context's internal goroutine
- Never store a context in a struct field; pass it as a function parameter
- Check `ctx.Err()` to distinguish `context.Canceled` from `context.DeadlineExceeded`

## Ring buffer (lossy bounded queue)

- Use a buffered channel with a non-blocking `select` to implement a ring buffer that drops oldest items when full

```go
select {
case out <- v:
default:
    <-out  // evict oldest
    out <- v
}
```

- This is appropriate for real-time telemetry or logging where stale data has less value than new data; never use it where dropping items silently is unacceptable

## Anti-patterns

- **Goroutine leak from abandoned producer**: a goroutine blocked on send to a channel no one is reading leaks forever — always provide a quit/done path
- **Unbuffered channel in scatter-gather**: if the consumer times out and stops receiving, senders block indefinitely — size the channel to the number of senders
- **`close()` on a channel while goroutines are still sending to it**: causes a panic — signal goroutines to stop (via quit or done) and wait for them to exit before closing
- **Blocking work inside a `select` loop**: a slow operation in a `select` case blocks all other cases (sends, closes) for its duration — run it in a sub-goroutine and deliver the result via a channel
- **`time.After` inside a loop for a global deadline**: creates a new timer on every iteration; the deadline never triggers — call it once outside the loop
- **Not calling `cancel()`**: leaks the context and its associated goroutine/resources until the parent context is cancelled
