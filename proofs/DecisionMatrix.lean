import JobDecision

def bit (value : Bool) : String := if value then "1" else "0"

def statusLabel : JobDecision.Status → String
  | .pass => "PASS"
  | .fail => "FAIL"
  | .review => "REVIEW"

def main : IO Unit := do
  for failed in [false, true] do
    for unknown in [false, true] do
      for sourceValid in [false, true] do
        let value := JobDecision.evaluate failed unknown sourceValid
        IO.println s!"{bit failed},{bit unknown},{bit sourceValid},{statusLabel value}"
