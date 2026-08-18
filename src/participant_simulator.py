"""
Participant simulator for federated learning scenarios.

This module takes a single DatasetData and divides it into multiple participants,
simulating a federated learning environment with configurable distribution modes.

Supports:
- IID distribution: Each participant gets random representative sample
- Non-IID distribution: Each participant gets skewed class distribution
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import time
from copy import deepcopy

from src.dataset_loader import DatasetData, DatasetMetadata


@dataclass
class ParticipantMetadata:
    """Metadata about a participant's dataset."""
    original_row_index: List[int]  # Which rows from original dataset
    class_distribution: Dict[int, int]  # {class_label: count}
    feature_count: int
    missing_value_count: int = 0
    duplicate_row_count: int = 0


@dataclass
class ParticipantData:
    """Data for a single federated participant."""
    participant_id: str  # e.g., "ORG-001"
    X: np.ndarray  # Feature matrix (N × M)
    y: np.ndarray  # Label vector (N,)
    row_count: int
    timestamp: float  # When this participant's data was created
    metadata: ParticipantMetadata
    
    def __post_init__(self):
        """Validate participant data integrity."""
        if len(self.X) != len(self.y):
            raise ValueError(
                f"Participant {self.participant_id}: Feature matrix ({len(self.X)} rows) "
                f"and labels ({len(self.y)} rows) have mismatched lengths"
            )
        
        if len(self.X) != self.row_count:
            raise ValueError(
                f"Participant {self.participant_id}: Row count mismatch "
                f"(declared {self.row_count}, actual {len(self.X)})"
            )


def simulate_participants(
    dataset: DatasetData,
    number_of_participants: int = 10,
    distribution_mode: str = "iid",
    random_seed: int = 42,
    verbose: bool = False
) -> List[ParticipantData]:
    """
    Divide a dataset into multiple simulated federated participants.
    
    Parameters
    ----------
    dataset : DatasetData
        Original dataset to partition (will NOT be modified)
    number_of_participants : int
        Number of simulated participants
    distribution_mode : str
        "iid" - IID distribution (random shuffle, equal split)
        "non-iid" - Non-IID distribution (class-skewed per participant)
    random_seed : int
        Random seed for deterministic splitting
    verbose : bool
        Print distribution details
    
    Returns
    -------
    List[ParticipantData]
        List of participant datasets, non-overlapping, exhaustive
    
    Raises
    ------
    ValueError
        If number_of_participants <= 0 or distribution_mode is invalid
    """
    
    # ========== VALIDATION ==========
    if number_of_participants <= 0:
        raise ValueError(f"number_of_participants must be > 0, got {number_of_participants}")
    
    if number_of_participants > len(dataset.X):
        raise ValueError(
            f"Cannot create {number_of_participants} participants from "
            f"dataset with only {len(dataset.X)} rows"
        )
    
    if distribution_mode not in ["iid", "non-iid"]:
        raise ValueError(
            f"distribution_mode must be 'iid' or 'non-iid', got '{distribution_mode}'"
        )
    
    # Set random seed for reproducibility
    rng = np.random.RandomState(random_seed)
    
    # Make deterministic copy of original data (never modify original)
    X_original = dataset.X.copy()
    y_original = dataset.y.copy()
    
    # ========== DISTRIBUTE DATA ==========
    if distribution_mode == "iid":
        participants = _distribute_iid(
            X_original, y_original, number_of_participants, rng, verbose
        )
    else:  # non-iid
        participants = _distribute_non_iid(
            X_original, y_original, number_of_participants, rng, verbose
        )
    
    # ========== VERIFY INTEGRITY ==========
    total_rows = sum(p.row_count for p in participants)
    if total_rows != len(X_original):
        raise RuntimeError(
            f"Data loss detected! Original: {len(X_original)} rows, "
            f"distributed: {total_rows} rows"
        )
    
    # Verify no overlapping indices
    all_indices = []
    for p in participants:
        all_indices.extend(p.metadata.original_row_index)
    
    if len(all_indices) != len(set(all_indices)):
        raise RuntimeError("Data overlap detected! Participants share rows.")
    
    if set(all_indices) != set(range(len(X_original))):
        raise RuntimeError("Not all rows distributed to participants.")
    
    return participants


def _distribute_iid(
    X: np.ndarray,
    y: np.ndarray,
    num_participants: int,
    rng: np.random.RandomState,
    verbose: bool = False
) -> List[ParticipantData]:
    """
    Distribute data in IID fashion: random shuffle, equal-sized chunks.
    
    Each participant gets approximately the same number of rows,
    with class distribution representative of the whole dataset.
    """
    
    n_samples = len(X)
    
    # Shuffle indices
    indices = np.arange(n_samples)
    rng.shuffle(indices)
    
    # Split into chunks
    chunk_size = n_samples // num_participants
    participants = []
    
    for i in range(num_participants):
        # Last participant gets remainder
        if i == num_participants - 1:
            start_idx = i * chunk_size
            end_idx = n_samples
        else:
            start_idx = i * chunk_size
            end_idx = (i + 1) * chunk_size
        
        participant_indices = indices[start_idx:end_idx]
        
        # Extract data for this participant
        X_participant = X[participant_indices].copy()
        y_participant = y[participant_indices].copy()
        
        # Build metadata
        unique_labels, counts = np.unique(y_participant, return_counts=True)
        class_dist = {int(label): int(count) for label, count in zip(unique_labels, counts)}
        
        metadata = ParticipantMetadata(
            original_row_index=participant_indices.tolist(),
            class_distribution=class_dist,
            feature_count=X_participant.shape[1],
            missing_value_count=0,
            duplicate_row_count=0
        )
        
        participant = ParticipantData(
            participant_id=f"ORG-{i+1:03d}",
            X=X_participant,
            y=y_participant,
            row_count=len(X_participant),
            timestamp=time.time(),
            metadata=metadata
        )
        
        participants.append(participant)
    
    if verbose:
        print(f"✓ IID Distribution: {num_participants} participants")
        for p in participants:
            print(f"  - {p.participant_id}: {p.row_count} rows, "
                  f"classes {p.metadata.class_distribution}")
    
    return participants


def _distribute_non_iid(
    X: np.ndarray,
    y: np.ndarray,
    num_participants: int,
    rng: np.random.RandomState,
    verbose: bool = False
) -> List[ParticipantData]:
    """
    Distribute data in non-IID fashion: class-skewed distribution.
    
    Each participant gets a skewed distribution of classes:
    - Some participants specialize in class 1
    - Others specialize in class 2, etc.
    - Ensures each participant has distinct class imbalance
    """
    
    n_samples = len(X)
    unique_labels = np.unique(y)
    num_classes = len(unique_labels)
    
    # Assign each participant a "primary class"
    primary_classes = np.tile(unique_labels, (num_participants // num_classes + 1))[:num_participants]
    
    participants = []
    used_indices = set()
    
    for i in range(num_participants):
        primary_class = primary_classes[i]
        
        # Get indices for this participant's data
        # Primary class: 60% of participant's data
        # Other classes: 40% split evenly
        
        class_indices = {}
        for label in unique_labels:
            class_indices[label] = np.where(y == label)[0]
        
        participant_indices = []
        
        # Add primary class data (60%)
        num_primary = max(1, n_samples // (num_participants * 2))
        primary_available = [idx for idx in class_indices[primary_class] if idx not in used_indices]
        
        if len(primary_available) > 0:
            selected_primary = rng.choice(
                primary_available,
                size=min(num_primary, len(primary_available)),
                replace=False
            )
            participant_indices.extend(selected_primary)
            used_indices.update(selected_primary)
        
        # Add secondary class data (40%)
        num_secondary = max(0, (n_samples // (num_participants * 5)))
        other_classes = [c for c in unique_labels if c != primary_class]
        
        for other_class in other_classes:
            secondary_available = [idx for idx in class_indices[other_class] if idx not in used_indices]
            
            if len(secondary_available) > 0:
                num_to_take = num_secondary // len(other_classes) if len(other_classes) > 0 else 0
                if num_to_take > 0:
                    selected_secondary = rng.choice(
                        secondary_available,
                        size=min(num_to_take, len(secondary_available)),
                        replace=False
                    )
                    participant_indices.extend(selected_secondary)
                    used_indices.update(selected_secondary)
        
        # Ensure each participant has at least some data
        if len(participant_indices) == 0:
            # Fallback: take some data from any available class
            available = [idx for idx in range(n_samples) if idx not in used_indices]
            if available:
                fallback_indices = rng.choice(available, size=min(5, len(available)), replace=False)
                participant_indices.extend(fallback_indices)
                used_indices.update(fallback_indices)
        
        # Shuffle participant's data
        participant_indices = np.array(list(set(participant_indices)))  # Remove duplicates
        rng.shuffle(participant_indices)
        
        # Extract data
        X_participant = X[participant_indices].copy()
        y_participant = y[participant_indices].copy()
        
        # Build metadata
        unique_p_labels, counts = np.unique(y_participant, return_counts=True)
        class_dist = {int(label): int(count) for label, count in zip(unique_p_labels, counts)}
        
        metadata = ParticipantMetadata(
            original_row_index=participant_indices.tolist(),
            class_distribution=class_dist,
            feature_count=X_participant.shape[1],
            missing_value_count=0,
            duplicate_row_count=0
        )
        
        participant = ParticipantData(
            participant_id=f"ORG-{i+1:03d}",
            X=X_participant,
            y=y_participant,
            row_count=len(X_participant),
            timestamp=time.time(),
            metadata=metadata
        )
        
        participants.append(participant)
    
    # Distribute remaining rows to participants (if any)
    available_indices = [idx for idx in range(n_samples) if idx not in used_indices]
    if available_indices:
        for i, idx in enumerate(available_indices):
            p_idx = i % num_participants
            participants[p_idx].X = np.vstack([participants[p_idx].X, X[idx:idx+1]])
            participants[p_idx].y = np.append(participants[p_idx].y, y[idx])
            participants[p_idx].row_count += 1
            participants[p_idx].metadata.original_row_index.append(idx)
            participants[p_idx].metadata.class_distribution[int(y[idx])] = \
                participants[p_idx].metadata.class_distribution.get(int(y[idx]), 0) + 1
    
    if verbose:
        print(f"✓ Non-IID Distribution: {num_participants} participants")
        for p in participants:
            print(f"  - {p.participant_id}: {p.row_count} rows, "
                  f"classes {p.metadata.class_distribution}")
    
    return participants


def verify_no_data_loss(
    original_dataset: DatasetData,
    participants: List[ParticipantData]
) -> bool:
    """
    Verify that data distribution preserved all original rows.
    
    Returns
    -------
    bool
        True if all rows accounted for, raises ValueError otherwise
    """
    
    total_participant_rows = sum(p.row_count for p in participants)
    original_rows = len(original_dataset.X)
    
    if total_participant_rows != original_rows:
        raise ValueError(
            f"Data loss detected! Original: {original_rows} rows, "
            f"distributed: {total_participant_rows} rows"
        )
    
    # Check for overlaps and gaps
    all_indices = []
    for p in participants:
        all_indices.extend(p.metadata.original_row_index)
    
    if len(set(all_indices)) != len(all_indices):
        raise ValueError("Data overlap: some rows assigned to multiple participants")
    
    if set(all_indices) != set(range(original_rows)):
        missing = set(range(original_rows)) - set(all_indices)
        raise ValueError(f"Data gap: rows {missing} not assigned to any participant")
    
    return True


def get_distribution_statistics(participants: List[ParticipantData]) -> Dict:
    """
    Calculate statistics about participant distribution.
    
    Returns
    -------
    Dict
        Statistics including row counts, class distributions, etc.
    """
    
    row_counts = [p.row_count for p in participants]
    
    total_rows = sum(row_counts)
    min_rows = min(row_counts)
    max_rows = max(row_counts)
    avg_rows = total_rows / len(participants)
    
    # Class distribution across all participants
    global_class_dist = {}
    for p in participants:
        for class_label, count in p.metadata.class_distribution.items():
            global_class_dist[class_label] = global_class_dist.get(class_label, 0) + count
    
    return {
        'num_participants': len(participants),
        'total_rows': total_rows,
        'avg_rows_per_participant': avg_rows,
        'min_rows': min_rows,
        'max_rows': max_rows,
        'row_count_std': float(np.std(row_counts)),
        'global_class_distribution': global_class_dist
    }
