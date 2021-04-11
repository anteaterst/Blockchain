import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request



# 블록체인 클래스는 블록체인을 저장하도록 만든다.
# 다른 거래들을 저장하는 역할 또한 맡게 될 것. (체인을 관리)

class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # 제네시스 블록을 만든다
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address):
        # 노드 목록에 새 노드 추가
        # :param address: 노드의 주소 예: 'http://192.168.0.5:5000'

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # '192.168.0.5:5000'과 같은 scheme이 없는 URL을 수락
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):
        # 지정된 블록체인이 유효한지 확인
        # : param chain : 블록체인
        # :return: True이면 True이고, 그렇지 않으면 False

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # 블록 해시가 올바른지 확인
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # 작업 증명서가 올바른지 확인
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        # 이 함수는 합의 알고리즘으로 충돌을 해결해주는 역할을 함
        # 우리 체인을 네트워크에서 가장 긴 체인으로 교체하는 과정을 거친다 
        # :return: 체인을 교체한경우 True, 그렇지 않은 경우는 False가 된다.

        neighbours = self.nodes
        new_chain = None

        # 우린 오직 우리보다 더 길다란 체인만 찾고 있음
        max_length = len(self.chain)

        # 네트워크의 모든 노드에서 체인 가져오기 및 확인
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # 길이가 더 길고 체인이 유효한지 점검
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # 우리보다 더 긴 유효한 새 체인을 발견하면 체인을 교체한다.
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash):
        # 블록체인에 새 블록 생성
        # :param previous_hash: 이전 블록의 해시
        # :return: 새 블록

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # 현재 트랜잭션 목록 재설정
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        # 새로운 트랜젝션을 생성하여 다음 채굴블록으로 이동시킨다.
        # :param sender: 보낸사람 주소
        # :param recipient: 수취인 주소
        # :param amount: 금액
        # :return: 이 트랜젝션을 보유할 블록의 인덱스

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        #블록의 SHA-256 해시를 생성
        # :param block: 블록


        # 딕셔너리가 제대로 주문되었는지 확인해야 함, 그렇지 않으면 일치하지 않는 해시가 생겨남
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        # 단순 작업 증명 알고리즘
        # - 해시(pp')에 선행 0이 포함된 숫자 p'를 찾는다
        # - 여기서 p는 이전의 증거가 되고 p'는 새로운 증거가 된다
        
        # :param last_block: 마지막 블록 <dict>
        # :return: <int>

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        # # 검증 확인
        # :param last_proof: <int> 이전의 증명
        # :param proof: <int>  현재의 증명
        # :param last_hash: <str> 이전 블록의 해시
        # :return: <bool> 맞으면 True 틀리면 False

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# 우리의 노드를 인스턴스화한다. 
app = Flask(__name__)

# 우리의 노드의 이름을 임의로 설정한다.
node_identifier = str(uuid4()).replace('-', '')

# Blockchain 클래스를 인스턴스화한다.
blockchain = Blockchain()



# /mine 의 endpoint를 만든다. (요청을 GET 하는 곳이다.)
@app.route('/mine', methods=['GET'])
def mine():
    # 우리는 다음 증거를 얻기 위해 작업 증명 알고리즘을 실행한다.
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # 우리는 증거를 찾은 것에 대한 보상을 받아야 하는데
    # 송신자는 "0"으로, 이 노드가 새 코인을 채굴했음을 나타냅니다.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # 새 블록을 체인에 추가하여 위조시킨다.
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


# /transactions/new 의 endpoint를 만든다. (여기에 우리가 데이터를 보내고 요청을 POST하는 곳이다.)
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # 필수 필드가 POST 데이터에 있는지 확인합니다.
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # 새로운 트랜젝션을 만든다
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201



# /chain 의 endpoint를 만든다. (전체 블록체인을 반환하는 곳이다.)
@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200



# 포트 5000번에서 서버를 돌린다.
if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)

