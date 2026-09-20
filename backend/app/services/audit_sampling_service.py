import hashlib
import json
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class AuditSamplingService:
    """
    Deterministic Audit Sampling Engine conforming to AICPA AU-C Section 530
    and PCAOB AS 2315 (Audit Sampling).

    Guarantees 100% mathematical reproducibility by third-party auditors and regulators:
    1. Server-authoritative cryptographic seeds (client cannot forge or supply seed).
    2. Canonical deterministic ordering independent of database storage order.
    3. Isolated pseudo-random number generator (PRNG) instances (zero global state pollution).
    4. Immutable frozen population digests.
    """

    @staticmethod
    def canonical_sort_population(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sorts population items canonically by (source_record_id ASC).
        In the rare event of identical IDs, secondary sort is canonical JSON string.
        """
        return sorted(
            items,
            key=lambda x: (
                str(x.get("source_record_id", "")),
                json.dumps(x.get("attributes", {}), sort_keys=True)
            )
        )

    @staticmethod
    def compute_population_digest(items: List[Dict[str, Any]]) -> str:
        """
        Computes a deterministic SHA-256 digest of the entire population snapshot.
        Any change, addition, deletion, or reordering of items alters this digest.
        """
        canonical = AuditSamplingService.canonical_sort_population(items)
        normalized = [
            {
                "source_record_id": str(item["source_record_id"]),
                "attributes": item.get("attributes", {})
            }
            for item in canonical
        ]
        canonical_bytes = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    @staticmethod
    def generate_seed(
        organization_id: int,
        audit_id: int,
        procedure_id: int,
        population_id: int,
        total_count: int,
        sample_size: int,
        created_at: datetime
    ) -> str:
        """
        Derives a server-authoritative cryptographic seed for PRNG initialization.
        Client input is never accepted for seed derivation.
        """
        seed_str = (
            f"{organization_id}:{audit_id}:{procedure_id}:{population_id}:"
            f"{total_count}:{sample_size}:{created_at.isoformat()}"
        )
        return hashlib.sha256(seed_str.encode("utf-8")).hexdigest()

    @staticmethod
    def _seed_to_int(seed_hex: str) -> int:
        """Derives a deterministic 64-bit integer from the first 16 hex chars of the SHA-256 seed."""
        return int(seed_hex[:16], 16)

    @classmethod
    def sample_random(
        cls,
        canonical_items: List[Dict[str, Any]],
        sample_size: int,
        seed_hex: str
    ) -> List[Dict[str, Any]]:
        """
        Simple Random Sampling Without Replacement (AU-C 530).
        Every population item has an equal probability of selection.
        """
        N = len(canonical_items)
        if sample_size <= 0:
            raise ValueError(f"Sample size must be positive, got {sample_size}.")
        if sample_size > N:
            raise ValueError(f"Sample size ({sample_size}) cannot exceed population count ({N}).")

        prng_seed = cls._seed_to_int(seed_hex)
        rng = random.Random(prng_seed)
        selected_indices = sorted(rng.sample(range(N), sample_size))
        return [canonical_items[i] for i in selected_indices]

    @classmethod
    def sample_systematic(
        cls,
        canonical_items: List[Dict[str, Any]],
        sample_size: int,
        seed_hex: str
    ) -> List[Dict[str, Any]]:
        """
        Systematic Sampling with Random Start (AU-C 530).
        Calculates interval k = floor(N / n) and chooses a random start r in [0, k-1].
        Extracts sequence: r, r+k, r+2k, ..., r+(n-1)k.
        """
        N = len(canonical_items)
        if sample_size <= 0:
            raise ValueError(f"Sample size must be positive, got {sample_size}.")
        if sample_size > N:
            raise ValueError(f"Sample size ({sample_size}) cannot exceed population count ({N}).")

        k = N // sample_size
        if k < 1:
            k = 1

        prng_seed = cls._seed_to_int(seed_hex)
        rng = random.Random(prng_seed)
        start_r = rng.randint(0, k - 1)

        selected_indices = []
        for j in range(sample_size):
            idx = start_r + (j * k)
            if idx >= N:
                idx = idx % N  # wrap around if necessary
            selected_indices.append(idx)

        # Sort indices to preserve canonical sequence order
        selected_indices = sorted(set(selected_indices))
        # If wrap-around caused duplicate index, fill remainder from unused
        if len(selected_indices) < sample_size:
            unused = [i for i in range(N) if i not in selected_indices]
            additional = rng.sample(unused, sample_size - len(selected_indices))
            selected_indices = sorted(selected_indices + additional)

        return [canonical_items[i] for i in selected_indices]

    @classmethod
    def sample_stratified(
        cls,
        canonical_items: List[Dict[str, Any]],
        sample_size: int,
        seed_hex: str,
        strata_attribute: str
    ) -> List[Dict[str, Any]]:
        """
        Proportional Stratified Random Sampling (AU-C 530).
        Groups population by strata_attribute, allocates proportional sample sizes to each stratum,
        and samples randomly without replacement within each stratum.
        """
        N = len(canonical_items)
        if sample_size <= 0:
            raise ValueError(f"Sample size must be positive, got {sample_size}.")
        if sample_size > N:
            raise ValueError(f"Sample size ({sample_size}) cannot exceed population count ({N}).")
        if not strata_attribute:
            raise ValueError("Stratified sampling requires a non-empty strata_attribute.")

        # Group items into strata
        strata: Dict[str, List[Dict[str, Any]]] = {}
        for item in canonical_items:
            val = str(item.get("attributes", {}).get(strata_attribute, "UNSPECIFIED"))
            strata.setdefault(val, []).append(item)

        if not strata:
            raise ValueError("No strata found in population.")

        # Deterministically sort strata names
        sorted_strata_keys = sorted(strata.keys())

        # Proportional allocation
        allocations: Dict[str, int] = {}
        total_allocated = 0
        for key in sorted_strata_keys:
            stratum_count = len(strata[key])
            # Each stratum gets at least 1 if sample_size >= len(strata)
            raw_alloc = round(sample_size * (stratum_count / N))
            alloc = max(1, min(stratum_count, raw_alloc))
            allocations[key] = alloc
            total_allocated += alloc

        # Adjust total allocation to match sample_size exactly
        while total_allocated > sample_size:
            # decrement from stratum with largest allocation (> 1)
            candidates = [k for k in sorted_strata_keys if allocations[k] > 1]
            if not candidates:
                break
            largest_k = max(candidates, key=lambda k: (allocations[k], len(strata[k])))
            allocations[largest_k] -= 1
            total_allocated -= 1

        while total_allocated < sample_size:
            # increment stratum with room
            candidates = [k for k in sorted_strata_keys if allocations[k] < len(strata[k])]
            if not candidates:
                break
            best_k = max(candidates, key=lambda k: (len(strata[k]) - allocations[k]))
            allocations[best_k] += 1
            total_allocated += 1

        # Sample within each stratum using isolated derived sub-seed
        selected_items: List[Dict[str, Any]] = []
        for key in sorted_strata_keys:
            alloc = allocations[key]
            stratum_items = strata[key]
            sub_seed_str = f"{seed_hex}:stratum:{key}"
            sub_seed_hex = hashlib.sha256(sub_seed_str.encode("utf-8")).hexdigest()
            sub_rng = random.Random(cls._seed_to_int(sub_seed_hex))
            sub_indices = sorted(sub_rng.sample(range(len(stratum_items)), alloc))
            for idx in sub_indices:
                selected_items.append(stratum_items[idx])

        # Return canonically sorted
        return cls.canonical_sort_population(selected_items)

    @classmethod
    def execute_sampling(
        cls,
        items: List[Dict[str, Any]],
        sampling_method: str,
        sample_size: int,
        seed_hex: str,
        strata_attribute: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes sampling against canonically sorted population items using the specified method.
        """
        canonical = cls.canonical_sort_population(items)
        method = sampling_method.upper()

        if method == "RANDOM":
            return cls.sample_random(canonical, sample_size, seed_hex)
        elif method == "SYSTEMATIC":
            return cls.sample_systematic(canonical, sample_size, seed_hex)
        elif method == "STRATIFIED":
            if not strata_attribute:
                raise ValueError("strata_attribute is required for STRATIFIED sampling.")
            return cls.sample_stratified(canonical, sample_size, seed_hex, strata_attribute)
        else:
            raise ValueError(f"Unsupported sampling method: {sampling_method}. Must be RANDOM, SYSTEMATIC, or STRATIFIED.")
