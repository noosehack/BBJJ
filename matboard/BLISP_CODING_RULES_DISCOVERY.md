# BLISP Coding Rules Discovery

Evidence-based rules for implementing Matboard in BLISP. Each rule cites its authoritative source.

---

## R1. BLISP is a financial DSL, not a general-purpose Lisp

**Source**: `blisp/docs/BLISP_STATE_2026_05.md:59`
> "It is not a general-purpose Lisp — it is a domain-specific language whose purpose is to compose financial transformations."

**Implication**: Matboard cannot assume general Lisp facilities. It works within the language's actual capabilities, not imagined ones.

---

## R2. Strict IR is the default — user-defined function calls are blocked in `-e` mode

**Source**: `blisp/docs/ARCHITECTURE.md:78-81`
> `BLISP_STRICT_IR` default is `1` (hard error on dangerous fallback).

**Source**: `blisp/src/hybrid.rs:258-270` — any unknown symbol in function position falls through to `LegacyDangerous`.

**Verified**: `blisp -e '(let* ((f (lambda (x) (+ x 1)))) (f 5))'` → `[STRICT_IR:ERROR] class=DANGEROUS op=f`

**Implication**: `define` + `lambda` cannot create callable functions from `-e` expressions. Use `defmacro` for cross-file abstractions, or `define` + `lambda` inside `--load` files (see R6).

---

## R3. `defmacro` is the correct abstraction mechanism

**Source**: `blisp/stdlib/core.cl` — entire stdlib uses `defmacro` exclusively (inc, dec, when, unless, and, or, ones_like, pnl, topk, lvg, etc.)

**Source**: `blisp/docs/ARCHITECTURE.md:101` — `->` is a macro expanded by normalizer before evaluation.

**Verified**: `(defmacro add1 (x) (list (quote +) x 1)) (print (add1 5))` → prints `6` under strict mode.

**Mechanism**: Macros expand at parse time, before the planner sees the call site. The planner only sees the expanded form.

**Implication**: Every Matboard "function" is a `defmacro`. Quasiquote (`` ` ``) and unquote (`,`) are available for template construction.

---

## R4. TUP, GET, KEYS, same, list, str-cat are Orch — always allowed

**Source**: `blisp/src/hybrid.rs:204-205`
```rust
"type-of" | "len" | ... | "TUP" | "GET" | "KEYS"
| "save-ref" | "hash-frame" | "same" | "str-cat" | "list" | ...
=> FallbackClass::Orch,
```

**Verified**:
- `(TUP :kind "CON" :actor "me")` → `(TUP :kind "CON" :actor "me")`
- `(GET (TUP :kind "CON" :actor "me") :kind)` → `"CON"`
- `(KEYS (TUP :kind "CON" :actor "me"))` → `(:kind :actor)`
- `(same "a" "a")` → `true`
- `(list 1 2 3)` → `(1 2 3)`
- `(str-cat "CGRD" "." "CTRL")` → `"CGRD.CTRL"`

**Implication**: Matboard state (CON tuples, ORI, GND, radicals) uses TUP. Field access uses GET. Comparison uses same. All work under strict mode.

---

## R5. Special forms are Orch — define, let*, if, cond, progn all work

**Source**: `blisp/src/hybrid.rs:196-197`
```rust
"if" | "cond" | "define" | "defparameter" | "setf" | "let" | "let*" | "lambda"
| "quote" | "defmacro" | "->" | "progn" | ... => FallbackClass::Orch,
```

**Verified**: `(progn (define myvar (TUP :k "v")) (print (GET myvar :k)))` → `"v"`

**Implication**: Matboard can freely use define for variable binding, let* for local scope, if/cond for logic, progn for sequencing. Only function *calls* to user-defined names are blocked.

---

## R6. `--load` files execute in legacy mode — `define` + `lambda` works

**Source**: `blisp/src/main.rs:1936-1949`
```rust
// Load files (always use legacy for --load files, as they may contain defmacro, etc.)
```

**Verified**: `define` + `lambda` works inside `--load` files. Nested lambda calls (one user-defined function calling another) also work correctly after the scope fix in `b0862e2`.

**Implication**: Matboard engine logic uses `define` + `lambda` inside `--load` files for all functions that need iteration over CON slots, predicate checking, RESOLVE, etc. `defmacro` is used for type constructors that must be available cross-file.

---

## R7. `.blisp` is a recognized file extension

**Source**: `blisp/src/main.rs:640`
```rust
if arg.ends_with(".lisp") || arg.ends_with(".cl") || arg.ends_with(".blisp") {
```

**Implication**: Matboard files can use `.blisp` extension.

---

## R8. LEGACY is temporary — not for new domain engines

**Source**: `blisp/CLAUDE.md:31-33`
> "Every public finance op must eventually reach IR. LEGACY is a temporary state."

**Source**: `blisp/CLAUDE.md:120`
> "If semantics are wrong, fix the kernel or add a new IR variant. Never use multiplicative corrections."

**Implication**: Matboard should not rely on `BLISP_STRICT_IR=0` or `--legacy` as a crutch. Use the Orch-classified facilities (TUP, GET, KEYS, same, list, str-cat, define, let*, if, cond, defmacro) which are architecturally permanent.

---

## R9. The canonical pipeline is mandatory

**Source**: `blisp/CLAUDE.md:18-22`
> ```
> parse -> normalize -> canonicalize -> plan -> optimize -> execute
> ```
> No stage may be skipped or reordered.

**Implication**: Matboard canonicalization (Z₂ × Z₂ symmetry from MATBOARD_V0_SPEC §7) must be expressed using the available BLISP constructs, not by bypassing the pipeline.

---

## R10. FPT infrastructure already exists in BLISP

**Source**: `blisp/src/hybrid.rs:209-217` — FPT operations are Orch-classified:
```
"fpt-get" | "fpt-keys" | "fpt-has" | "fpt-between" | "fpt-since" | "fpt-table"
"FPR" | "FPR?" | "FPR-HSH" | "DIC-HSH" | "FPR->MOR" | "MOR->SRH"
"MOR-HSH" | "MOR-EQ?" | "MOR-CANON" ...
```

**Implication**: Matboard FPT records (TURN_FPT, GAME_FPT from MATBOARD_V0_SPEC §8) should use BLISP's existing FPT infrastructure where possible.

---

## R11. Lambda scope fix: nested calls preserve caller bindings (b0862e2)

**Bug**: `apply_lambda` in `eval.rs` called `restore_and_push(captured_env)` which replaced the entire lexical frame stack with the callee's captured environment. After the inner lambda returned, the caller's parameter bindings were gone.

**Failing pattern**:
```lisp
(define f (lambda (x) (same x nil)))
(define g (lambda (st)
  (if (f (GET st :c0)) true
      (if (f (GET st :c1)) true false))))  ;; "Undefined variable: st"
```

**Fix** (commit `b0862e2`): `apply_lambda` and `call_value` now save the caller's environment before entering the callee's closure, and restore it after the call completes. Same pattern `macroexpand_1` already used. 7 regression tests added (`tests/lambda_scope.rs`).

**Verified**: The Matboard 8-slot CON scan pattern now works:
```lisp
(define state-has-con (lambda (st con)
  (if (con-eq-safe (GET st :c0) con) true
  (if (con-eq-safe (GET st :c1) con) true
  ...
  false))))))))
```

**Implication**: Matboard can use `define` + `lambda` for all engine logic inside `--load` files, including nested function calls across multiple levels.

---

## Summary: Available Matboard Toolkit

| Facility | BLISP construct | Status |
|----------|----------------|--------|
| Type constructors | `(TUP :field val ...)` | Orch, works |
| Field access | `(GET tup :field)` | Orch, works |
| Key enumeration | `(KEYS tup)` | Orch, works |
| Equality | `(same a b)` | Orch, works |
| Lists | `(list a b c)` | Orch, works |
| String concat | `(str-cat a b)` | Orch, works |
| Variable binding | `(define name val)` | Orch, works |
| Local scope | `(let* ((x v)) body)` | Orch, works |
| Conditionals | `(if test then else)` | Orch, works |
| Multi-clause | `(cond (t1 e1) ...)` | Orch, works |
| Sequencing | `(progn e1 e2 ...)` | Orch, works |
| Reusable abstractions | `(defmacro name (args) body)` | Orch, works |
| Quasiquote | `` `(form ,var) `` | Parse-time, works |
| Output | `(print val)` | Orch, works |
| Function calls (`-e`) | `(user-func arg)` | **BLOCKED** under strict IR |
| Function calls (`--load`) | `(user-func arg)` | Works (legacy mode, scope fix b0862e2) |
| `--legacy` mode | `BLISP_STRICT_IR=0` | Escape hatch, not for production |
