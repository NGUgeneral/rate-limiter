install-buf:
	go install github.com/bufbuild/buf/cmd/buf@latest

generate-proto: install-buf
	buf lint
	buf generate