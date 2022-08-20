import typing as t

import numpy as np
from scipy.optimize import linear_sum_assignment

from ..tracks import Tracks
from .base import MOTMetricBase

_EPS = 1 / 1000


class HOTAResults(t.TypedDict):
    HOTA: float
    DetA: float
    AssA: float
    LocA: float
    alphas_HOTA: np.ndarray
    HOTA_alpha: np.ndarray
    DetA_alpha: np.ndarray
    AssA_alpha: np.ndarray
    LocA_alpha: np.ndarray


class HOTAMetrics(MOTMetricBase):
    def calculate_hota_metrics(
        self, ground_truth: Tracks, hypotheses: Tracks
    ) -> HOTAResults:

        gts = tuple(ground_truth.ids_count.keys())
        gts_counts = tuple(ground_truth.ids_count.values())
        hyps = tuple(hypotheses.ids_count.keys())
        hyps_counts = tuple(hypotheses.ids_count.values())
        n_gt, n_hyp = len(gts), len(hyps)

        alphas = np.arange(0.05, 0.96, 0.05)  # from 0.05 to 0.95 inclusive

        # The arrays should all have the shape [n_alphas, n_gt, n_hyp]
        TPA_max = np.zeros((len(alphas), n_gt, n_hyp), dtype=np.int32)
        FPA_max = np.tile(np.tile(hyps_counts, (n_gt, 1)), (len(alphas), 1, 1))
        FNA_max = np.tile(np.tile(gts_counts, (n_hyp, 1)).T, (len(alphas), 1, 1))

        TPA, FPA, FNA = TPA_max.copy(), FPA_max.copy(), FNA_max.copy()
        FP = np.ones((len(alphas),)) * sum(hyps_counts)
        FN = np.ones((len(alphas),)) * sum(gts_counts)
        LocAs = np.zeros((len(alphas),))  # Accumulator of similarities

        # Do the optimisitc matching - allow multiple matches per gt/hyp in same frame
        for frame in sorted(set(ground_truth.frames).intersection(hypotheses.frames)):
            dist_matrix = self._get_iou_frame(frame)

            gt_idx_ids = [gts.index(x) for x in ground_truth[frame].ids]
            hyp_idx_ids = [hyps.index(x) for x in hypotheses[frame].ids]

            for a_ind in range(len(alphas)):
                for row_ind, col_ind in np.argwhere(dist_matrix < alphas[a_ind]):
                    TPA_max[a_ind, gt_idx_ids[row_ind], hyp_idx_ids[col_ind]] += 1

        # Compute optimistic A_max, to be used for actual matching
        A_max = TPA_max / (FNA_max + FPA_max - TPA_max)

        # Do the actual matching
        for frame in sorted(set(ground_truth.frames).intersection(hypotheses.frames)):
            dist_matrix = self._get_iou_frame(frame)

            gt_idx_ids = [gts.index(x) for x in ground_truth[frame].ids]
            hyp_idx_ids = [hyps.index(x) for x in hypotheses[frame].ids]

            for a_ind in range(len(alphas)):
                opt_matrix = ((dist_matrix < alphas[a_ind]) / _EPS).astype(np.float64)
                opt_matrix += A_max[a_ind][np.ix_(gt_idx_ids, hyp_idx_ids)]
                opt_matrix += (1 - dist_matrix) * _EPS

                # Calculate matching as a LAP
                matching_inds = linear_sum_assignment(opt_matrix, maximize=True)
                for row_ind, col_ind in zip(*matching_inds):
                    if dist_matrix[row_ind, col_ind] < alphas[a_ind]:
                        TPA[a_ind, gt_idx_ids[row_ind], hyp_idx_ids[col_ind]] += 1
                        LocAs[a_ind] += 1 - dist_matrix[row_ind, col_ind]

        # Compute proper scores
        TP = TPA.sum(axis=(1, 2))
        A = TPA / (FNA + FPA - TPA)
        DetAs = TP / (FN + FP - TP)
        AssAs = (TPA * A).sum(axis=(1, 2)) / np.maximum(TP, 1)
        HOTAs = np.sqrt(DetAs * AssAs)

        # If no matches -> full similarity [strange default]
        LocAs = np.maximum(LocAs, 1e-10) / np.maximum(TP, 1e-10)

        return {
            "HOTA": HOTAs.mean(),
            "DetA": DetAs.mean(),
            "AssA": AssAs.mean(),
            "LocA": LocAs.mean(),
            "alphas_HOTA": alphas,
            "HOTA_alpha": HOTAs,
            "DetA_alpha": DetAs,
            "AssA_alpha": AssAs,
            "LocA_alpha": LocAs,
        }
