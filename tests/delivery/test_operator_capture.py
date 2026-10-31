import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'plugins/delivery/scripts'))
from operator_capture import CaptureAuthority, CaptureError, question_digest


class OperatorCaptureTests(unittest.TestCase):
    def setUp(self):
        self.authority = CaptureAuthority()
        q = {'command': 'synthetic check', 'threadId': 'thread-1', 'turnId': 'turn-1', 'itemId':'item-1'}
        self.binding = {'request_id':'request-1','native_request_id':22,'thread_id':'thread-1',
            'turn_id':'turn-1','method':'item/commandExecution/requestApproval','item_id':'item-1',
            'question_digest':question_digest(q),'source_revision':'a'*40,'scope':{'role':'builder','cwd':'synthetic-worktree'},'question':q}

    def capture(self, authority=None, line='accept\n', binding=None):
        authority = authority or self.authority
        challenge = authority.challenge(binding or self.binding)
        # A real OS PTY exercises channel plumbing; automated input is synthetic,
        # not evidence a human manually approved anything.
        master, slave = os.openpty()
        terminal = io.TextIOWrapper(io.FileIO(slave,'r+',closefd=True), encoding='utf-8', write_through=True)
        try:
            os.write(master, line.encode())
            return authority.capture_from_terminal(challenge, terminal=terminal)
        finally:
            terminal.close()
            os.close(master)

    def test_pty_receipt_binds_source_scope_request_and_is_one_use(self):
        receipt = self.capture()
        self.assertEqual(self.authority.verify_receipt(receipt,self.binding),{'decision':'accept'})
        with self.assertRaises(CaptureError):
            self.authority.verify_receipt(receipt,self.binding)

    def test_arbitrary_answer_or_peer_receipt_is_not_provenance(self):
        with self.assertRaises(CaptureError):
            self.authority.verify_receipt({'decision':'accept','actor':'owner'},self.binding)
        peer = CaptureAuthority()
        with self.assertRaises(CaptureError):
            self.authority.verify_receipt(self.capture(peer),self.binding)

    def test_answer_tampering_and_changed_head_scope_question_are_rejected(self):
        receipt=self.capture()
        forged=copy.deepcopy(receipt);forged['response']['decision']='decline'
        with self.assertRaises(CaptureError):self.authority.verify_receipt(forged,self.binding)
        for field,value in [('source_revision','b'*40),('scope',{'role':'manager'}),('turn_id','turn-2'),('request_id','request-2')]:
            changed={**self.binding,field:value}
            with self.assertRaises(CaptureError):self.authority.verify_receipt(receipt,changed)
        changed=copy.deepcopy(self.binding);changed['question']['command']='different command';changed['question_digest']=question_digest(changed['question'])
        with self.assertRaises(CaptureError):self.authority.verify_receipt(receipt,changed)
        self.assertEqual(self.authority.verify_receipt(receipt,self.binding),{'decision':'accept'})

    def test_revocation_expiry_and_restart_never_replay(self):
        receipt=self.capture();self.authority.revoke(receipt['challenge']['nonce'])
        with self.assertRaises(CaptureError):self.authority.verify_receipt(receipt,self.binding)
        receipt=self.capture()
        with patch('operator_capture.time.time',return_value=receipt['challenge']['expires_at']+1):
            with self.assertRaises(CaptureError):self.authority.verify_receipt(receipt,self.binding)
        receipt=self.capture()
        with self.assertRaises(CaptureError):CaptureAuthority().verify_receipt(receipt,self.binding)
        self.authority.revoke_all()
        with self.assertRaises(CaptureError):self.authority.verify_receipt(receipt,self.binding)

    def test_non_terminal_and_session_wide_or_empty_decisions_are_rejected(self):
        challenge=self.authority.challenge(self.binding)
        with tempfile.TemporaryFile(mode='w+') as stream:
            stream.write('accept\n');stream.seek(0)
            with self.assertRaises(CaptureError):self.authority.capture_from_terminal(challenge,terminal=stream)
        for line in ['acceptForSession\n','\n','{"decision":"accept","actor":"owner"}\n']:
            with self.assertRaises(CaptureError):self.capture(line=line)

    def test_challenge_cannot_change_the_rendered_question(self):
        challenge=self.authority.challenge(self.binding)
        challenge['binding']['question']['command']='forged'
        with self.assertRaises(CaptureError):self.authority.capture_from_terminal(challenge,terminal=io.StringIO('accept\n'))
        broken={**self.binding,'question_digest':'bad'}
        with self.assertRaises(CaptureError):self.authority.challenge(broken)

    def test_user_input_requires_all_exact_questions_without_defaults(self):
        binding={**self.binding,'method':'item/tool/requestUserInput','question':{'questions':[{'id':'choice','question':'Select a synthetic option','options':[{'label':'one'},{'label':'two'}]}]}}
        binding['question_digest']=question_digest(binding['question'])
        for answer in [{'answers':{}},{'answers':{'wrong':{'answers':['one']}}},{'answers':{'choice':{'answers':[]}}}]:
            with self.assertRaises(CaptureError):self.capture(line=json.dumps(answer)+'\n',binding=binding)
        value={'answers':{'choice':{'answers':['one']}}}
        receipt=self.capture(line=json.dumps(value)+'\n',binding=binding)
        self.assertEqual(self.authority.verify_receipt(receipt,binding),value)

    def test_delivery_gate_receipt_preserves_exact_attestation_scope(self):
        q={'attestation':'Synthetic accept head and criteria','options':['accept','decline','cancel']}
        binding={**self.binding,'method':'delivery/gateAcceptance','scope':{'issue':'synthetic-1','head':'a'*40,'criteria_hash':'b'*64},'question':q,'question_digest':question_digest(q)}
        receipt=self.capture(line='accept\n',binding=binding)
        wrong={**binding,'scope':{**binding['scope'],'head':'c'*40}}
        with self.assertRaises(CaptureError):self.authority.verify_receipt(receipt,wrong)
        self.assertEqual(self.authority.verify_receipt(receipt,binding),{'decision':'accept'})
