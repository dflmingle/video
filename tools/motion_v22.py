"""V22 soft red cohesion. V17 alone owns integration, collision and gait.

No root assignment, squad translation, healthy hit propagation or global phase.
Formation influence is a bounded acceleration added before existing steering.
"""
import math
import numpy as np
from motion_v17 import Crowd as CrowdV17


class Crowd(CrowdV17):
    def __init__(self, units, config):
        super().__init__(units, config)
        self.formationAcceleration = np.zeros((self.n, 2))
        self.cohesionPressure = np.zeros(self.n)

    def compute_desired_speed(self, i, t, congestion):
        # V21 multiplied a second injury penalty over this existing per-person
        # wound model. Keep exactly ONE wound factor and no squad slowdown.
        rhythm = (.035 * math.sin(t * self.rhythmA[i] + self.phaseA[i]) +
                  .020 * math.sin(t * self.rhythmB[i] + self.phaseB[i]))
        self.effort[i] = rhythm / .055
        return max(0., self.preferred[i] * (1 + rhythm) * congestion *
                   self.get_hit_speed_multiplier(i, t))

    def compute_soft_formation_correction(self, i):
        # Return no velocity correction: acceleration is integrated below.
        p = self.pressure[i]
        lateral_free = .18 + .36 * p
        longitudinal_free = 1.15 + 1.65 * p
        dx = self.initial[i, 0] - self.position[i, 0]
        x_error = math.copysign(max(0., abs(dx) - lateral_free), dx)
        progress = self.position[i, 1] - self.initial[i, 1]
        dz = self.progressMedian[i] - progress
        # Only obviously over-advanced members receive a small correction.
        # Do not turn healthy rear ranks into a slower shared pace controller.
        z_error = min(0., dz + longitudinal_free)
        # No formation rescue for wounded/dead people: others pass their body.
        if self.hp[i] < self.config['redHitPoints']:
            z_error = 0.
        lateral_strength = 6. - 3. * p
        longitudinal_strength = 10. - 7. * p
        self.formationAcceleration[i] = [np.clip(x_error * lateral_strength, -2.4, 2.4),
                                         np.clip(z_error * longitudinal_strength, -2.2, 0.)]
        return 0.

    def compute_local_avoidance(self, i, neighbors, t):
        lateral = super().compute_local_avoidance(i, neighbors, t)
        # Actual speed-ratio clamp, replacing V21's always-one multiplier.
        ratio = .30 if self.route[i] >= 0 else .20
        forward = max(1., float(self.velocity[i, 1]))
        limit = min(2., ratio * forward)
        return float(np.clip(lateral, -limit, limit))

    def limit_steering_and_speed(self, i, desired, dt):
        # Preserve V17's real acceleration/turn limiter exactly. The former
        # .20s forward servo reduced startup acceleration; congestion amplified
        # that lag through successive ranks. No extra velocity low-pass here.
        # Formation acceleration is deliberately a small target correction,
        # converted from world units/s^2 to units/s exactly once.
        adjusted = desired + self.formationAcceleration[i] * dt
        adjusted[1] = max(0., adjusted[1])
        return super().limit_steering_and_speed(i, adjusted, dt)
