"""V21 blue archer controller: soft stable slot offsets and staggered attack readiness.
Compatible with the V18 12-column blue-control interface."""
import math
import numpy as np
from archers_v18 import Archers as ArchersV18

class Archers(ArchersV18):
    """Preserve U endpoints while allowing a small deterministic soft-slot drift."""
    def __init__(self, units, C):
        super().__init__(units, C)
        self.slotOffsets = np.zeros((self.n, 2), dtype=np.float64)
        self.squadWave = np.zeros(self.n, dtype=np.float64)
        for j, u in enumerate(self.units):
            # Stable low-discrepancy offsets: no per-frame noise and no large spread.
            q = ((j + 1) * 0.61803398875) % 1.0
            q2 = ((j + 1) * 0.41421356237 + u['group'] * .173) % 1.0
            lateral = (q - .5) * min(.14, C.get('blueSpacing', .94) * .14)
            depth = (q2 - .5) * .055
            self.slotOffsets[j] = [lateral, depth]
            # Left / center / right wings and individuals begin attack readiness
            # on a shallow wave; this is added to aiming, not release teleportation.
            groupWave = [0.0, .028, .052, .072, .058, .034, .012][int(u['group'])]
            self.squadWave[j] = groupWave + .018 * q2
            u['slotOffset'] = self.slotOffsets[j].tolist()
            u['attackStartOffset'] = float(self.squadWave[j])
            u['aimSeconds'] = float(u['aimSeconds'] + self.squadWave[j])
        self._rebuild_soft_paths()

    def _rebuild_soft_paths(self):
        # Offset only the deployment corridor's terminal portion. Starts remain
        # exactly authored; U endpoints shift by < 0.07 world units.
        for j, u in enumerate(self.units):
            base = self.pathPoints[j]
            s = np.linspace(0.0, 1.0, len(base))
            smooth = s * s * (3.0 - 2.0 * s)
            offset = self.slotOffsets[j]
            path = base.copy()
            path[:, 0] += float(offset[0]) * smooth
            path[:, 1] += float(offset[1]) * smooth
            seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
            cum = np.concatenate([[0.0], np.cumsum(seg)])
            self.pathPoints[j] = path
            self.pathCum[j] = cum
            u['deploymentPathLength'] = float(cum[-1])
            # Preserve each archer's original duration while recalibrating speed.
            u['walkSpeed'] = u['deploymentPathLength'] / max(u['moveSeconds'], 1e-4) * (.91 + .16 * (((j + 1) * .41421356237) % 1.0))
            u['target'] = [float(u['start'][0] + offset[0]), float(u['start'][1] - self.C['blueAdvance'] + offset[1])]

    def control(self):
        # Keep V18's first 12 fields exactly stable; no renderer changes required.
        return super().control()
