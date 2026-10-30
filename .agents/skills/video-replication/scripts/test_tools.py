"""Behavioral regression for provenance, matching, motion safety and registration."""
import unittest
import cv2
import numpy as np
from common import evidence
from reconstruction import stable_mask_layout, occupation_quantiles, continuous_min_distance, resolve, fit_path
from vision import register, associate, binary_metrics
from replicate import check_bundle, observation_at

class Tests(unittest.TestCase):
    def test_segment_last_frame_float_roundoff(self):
        fps=30000/1001;rows=[dict(t=f/fps,center=[f,0]) for f in range(90,120)]
        t=90/fps+29/fps
        self.assertEqual(observation_at(rows,t+1e-14,.1,'contour')['center'],[119,0])
        self.assertIsNone(observation_at(rows,121/fps,.1,'contour'))

    def test_stable_assignment_and_nonrectangular_support(self):
        m=np.zeros((40,40),np.uint8);m[2:35,2:12]=255;m[25:35,2:35]=255
        old=np.array([[5,5],[7,30],[25,30]],float)
        new=stable_mask_layout(m,old)
        self.assertTrue(all(m[int(y),int(x)] for x,y in new))
        self.assertEqual(len(np.unique(new,axis=0)),3)
        np.testing.assert_equal(new,stable_mask_layout(m,old))
        pts=occupation_quantiles(m,[[.05,.1],[.5,.5],[.95,.9]])
        self.assertTrue(all(m[int(y),int(x)] for x,y in pts))

    def test_between_frame_collision(self):
        self.assertAlmostEqual(continuous_min_distance([0,0],[10,0],[10,0],[0,0]),0)

    def test_absolute_override_and_conflict(self):
        layers=[dict(id='group',priority=1,start=0,end=2,position=[1,1],inputs_hash='a'),dict(id='member',priority=2,start=0,end=2,position=[9,9],inputs_hash='b')]
        self.assertEqual(resolve(layers,1)['position'],[9,9])
        layers[1]['priority']=1
        with self.assertRaises(ValueError):resolve(layers,1)

    def test_assignment_rejects_far_candidate(self):
        act={'one':[dict(t=0,center=[0,0])]}
        self.assertEqual(associate(act,[dict(center=[100,100])],1,10,2),{})

    def test_registration_recovers_known_shift_and_rejects_blank(self):
        rng=np.random.default_rng(10);im=np.uint8(rng.random((200,240,3))*255)
        M=np.float32([[1,0,7],[0,1,4]])
        r=register(im,cv2.warpAffine(im,M,(240,200)))
        self.assertEqual(r['status'],'PASS');np.testing.assert_allclose(np.array(r['matrix'])[:2,2],[7,4],atol=.5)
        self.assertIsNone(register(np.zeros_like(im),im)['matrix'])

    def test_empty_mask_not_perfect_match(self):
        m=np.zeros((20,20),np.uint8)
        self.assertIsNone(binary_metrics(m,m)['iou'])

    def test_bounded_fit_and_heldout_label(self):
        r=fit_path([0,1,2],[[0,0],[1,0],[2,0]],[0,2],[[0,1],[2,1]],.1,2)
        self.assertTrue(r['success']);self.assertIn('HELDOUT',r['validation'])

    def test_illegal_emission_resurrection_and_synthetic_claim(self):
        ev=evidence('AUTOMATIC','INFERRED',[{'frame':0}])
        b=dict(analysis=dict(start=0,end=2),objects=[dict(id='x',type='DISPLAY_MEMBER',evidence=ev,
            states=[dict(t=0,state='DEAD_HIDDEN'),dict(t=1,state='ALIVE')],observations=[])],events=[
            dict(id='bad',kind='FIRE',t=1,actor_id='x',evidence=evidence('RULE_GENERATED','SYNTHETIC',[{'rule':'test'}]))])
        r=check_bundle(b,1,100,1)
        self.assertEqual(r['engineering_status'],'FAIL')
        self.assertTrue(any('RESURRECTION' in s for s in r['failures']))
        self.assertTrue(any('DISABLED_ACTOR' in s for s in r['failures']))
        self.assertTrue(any('AUTHORIZATION' in s for s in r['failures']))

if __name__=='__main__':unittest.main(verbosity=2)
