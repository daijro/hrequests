# Makefile

vermin:
	vermin --eval-annotations --target=3.8 --violations .

gotidy:
	cd bridge && \
	go get -u && \
	go mod tidy && \
	rm -rf dist

build:
	cd bridge && \
	rm -rf dist && \
	VERSION=$$(cat VERSION) && \
	xgo --out=hrequests-cgo-$$VERSION -buildmode=c-shared --dest=./dist .
