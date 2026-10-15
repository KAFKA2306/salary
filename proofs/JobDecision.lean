import Init

/-!
Pure decision summary of the eight job eligibility gates:
- known failure dominates all other evidence;
- unknown or invalid source is REVIEW (not a pass);
- publication requires every gate to pass and a valid source.
The production Python bridge checks the eight abstract boolean combinations.
-/

namespace JobDecision

inductive Status where
  | pass | fail | review
  deriving BEq, Repr, DecidableEq

def evaluate (anyFail anyUnknown sourceValid : Bool) : Status :=
  if anyFail then .fail
  else if anyUnknown || !sourceValid then .review
  else .pass

def publish (status : Status) : Bool := status == .pass

theorem known_failure_always_rejected (u source : Bool) :
    evaluate true u source = .fail := rfl

theorem unknown_never_published (source : Bool) :
    publish (evaluate false true source) = false := by
  cases source <;> decide

theorem missing_source_never_published (u : Bool) :
    publish (evaluate false u false) = false := by
  cases u <;> decide

/-- Full necessary and sufficient condition for publication. -/
theorem publish_iff_no_failed_or_unknown_gate_and_valid_source
    (f u s : Bool) :
    publish (evaluate f u s) = true ↔
      f = false ∧ u = false ∧ s = true := by
  cases f <;> cases u <;> cases s <;> decide

end JobDecision
