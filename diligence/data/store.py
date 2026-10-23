"""In-memory registry of the reference dataset and uploaded datasets.

Uploaded datasets are deliberately ephemeral: they live in process memory
for ``ttl_seconds`` and are never written to disk. They are addressed by an
unguessable random id, which the browser keeps for the session. This suits
a stateless free hosting tier and avoids storing user data permanently.
"""

from __future__ import annotations

import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from diligence.data.ingest import ColumnMapping, build_records, load_dataset, map_columns, read_csv_bytes
from diligence.ml.model import ModelService

REFERENCE_ID = "reference"


@dataclass
class Dataset:
    id: str
    name: str
    kind: str
    records: list[dict[str, Any]]
    mapping: ColumnMapping
    created_at: float = field(default_factory=time.time)
    source_columns: list[str] = field(default_factory=list)
    index: dict[str, dict[str, Any]] = field(init=False)

    def __post_init__(self) -> None:
        self.index = {record["id"]: record for record in self.records}

    @property
    def scored(self) -> list[dict[str, Any]]:
        return [record for record in self.records if record.get("prediction")]

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "rows": len(self.records),
            "scored_rows": len(self.scored),
            "rows_with_issues": sum(1 for record in self.records if record["issues"]),
            "has_status": any(record.get("status") for record in self.records),
            "column_mapping": self.mapping.as_dict(),
            "unused_columns": self.mapping.unused,
            "created_at": self.created_at,
        }


def safe_display_name(filename: str | None) -> str:
    """Keep a short, harmless display name; the file is never saved under it."""
    base = Path(filename or "upload.csv").name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", base).strip(" ._") or "upload.csv"
    return cleaned[:80]


class DatasetStore:
    def __init__(self, model: ModelService, reference_path: Path, ttl_seconds: int = 7200, max_uploads: int = 20):
        self.model = model
        self.ttl_seconds = ttl_seconds
        self.max_uploads = max_uploads
        self._uploads: dict[str, Dataset] = {}
        self._lock = threading.Lock()
        self.reference = self._load_reference(reference_path)

    def _load_reference(self, path: Path) -> Dataset:
        frame = read_csv_bytes(path.read_bytes())
        mapping = map_columns(list(frame.columns))
        records = build_records(frame, mapping)
        evaluation = self.model.reference_evaluation.set_index("id")
        for record in records:
            if record["id"] in evaluation.index:
                row = evaluation.loc[record["id"]]
                record["evaluation_split"] = str(row["split"])
                record["out_of_fold_probabilities"] = {
                    label: float(row[f"oof_{label.lower()}"]) for label in self.model.classes
                }
        self._score(records)
        training_inputs = [record["model_input"] for record in records if record.get("evaluation_split") == "train"]
        self.model.set_background(training_inputs, size=50)
        dataset = Dataset(
            id=REFERENCE_ID,
            name="Y Combinator reference dataset (2005-2014)",
            kind="reference",
            records=records,
            mapping=mapping,
            source_columns=list(frame.columns),
        )
        return dataset

    def _score(self, records: list[dict[str, Any]]) -> None:
        scorable = [record for record in records if record["model_input"] is not None]
        for record, prediction in zip(scorable, self.model.predict([r["model_input"] for r in scorable])):
            record["prediction"] = prediction
        for record in records:
            record.setdefault("prediction", None)

    def add_upload(self, content: bytes, filename: str | None) -> Dataset:
        records, mapping, frame = load_dataset(content)
        self._score(records)
        dataset = Dataset(
            id=secrets.token_urlsafe(16),
            name=safe_display_name(filename),
            kind="upload",
            records=records,
            mapping=mapping,
            source_columns=list(frame.columns),
        )
        with self._lock:
            self._expire()
            while len(self._uploads) >= self.max_uploads:
                oldest = min(self._uploads.values(), key=lambda item: item.created_at)
                del self._uploads[oldest.id]
            self._uploads[dataset.id] = dataset
        return dataset

    def get(self, dataset_id: str | None) -> Dataset | None:
        if not dataset_id or dataset_id == REFERENCE_ID:
            return self.reference
        with self._lock:
            self._expire()
            return self._uploads.get(dataset_id)

    def delete(self, dataset_id: str) -> bool:
        with self._lock:
            return self._uploads.pop(dataset_id, None) is not None

    def _expire(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        for key in [key for key, value in self._uploads.items() if value.created_at < cutoff]:
            del self._uploads[key]
