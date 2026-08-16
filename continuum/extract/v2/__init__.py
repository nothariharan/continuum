"""V2 claim extraction — founder-led experimental pipeline.

Architecture (per the extraction-v2 plan):
    Artifact
      -> evidence envelope        (deterministic source metadata)
      -> timestamp resolver       (artifact ts -> header/slug/text signals)
      -> candidate detection      (lexicon-gated entity mentions)
      -> relation extraction      (constrained predicates between candidates)
      -> candidate claims         (schema-valid, evidence-grounded)

Everything in this package is an experiment on the extraction-v2 branch.
The shared contract (continuum.claims.schema) is untouched; the graph side
is untouched. Output must be consumable by scripts/checkpoint_claims.py.
"""
