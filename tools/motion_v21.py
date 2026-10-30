"""V21 red motion overlay.

Keeps motion_v17 as the authoritative collision/formation integrator and adds
bounded, event-driven local response.  Healthy members keep the existing
forward charge; recent hits only reduce the affected member's desired speed
and widen its local avoidance allowance for a short, decaying interval.
"""
from motion_v17 import Crowd as CrowdV17
from local_response_v21 import LocalResponseV21


class Crowd(CrowdV17):
    def __init__(self, units, config):
        super().__init__(units, config)
        self.localResponse = LocalResponseV21(units, config)
        self.response = self.localResponse.update(
            0.0, self.position, hp=self.hp, velocity=self.velocity,
            blue_positions=self.bluePositions, alive=~self.dead
        )

    def apply_hit(self, i, damage, t):
        super().apply_hit(i, damage, t)
        self.localResponse.record_hit(i, damage, t, killed=bool(self.dead[i]))

    def compute_desired_speed(self, i, t, congestion):
        base = super().compute_desired_speed(i, t, congestion)
        if self.response is None:
            return base
        return base * float(self.response['speedMultiplier'][i])

    def compute_local_avoidance(self, i, neighbors, t):
        lateral = super().compute_local_avoidance(i, neighbors, t)
        if self.response is None:
            return lateral
        limit = float(self.response['lateralLimit'][i])
        return float(max(-2.0, min(2.0, lateral))) * min(1.0, limit / 0.20)

    def step(self, t, dt=1 / 60):
        self.response = self.localResponse.update(
            t, self.position, hp=self.hp, velocity=self.velocity,
            blue_positions=self.bluePositions, alive=~self.dead
        )
        return super().step(t, dt)
