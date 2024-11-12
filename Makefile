# Helper for common actions

update-cgo:
	cd bridge && \
	go get -u && \
	go mod tidy && \
	rm -rf dist

build-cgo:
	cd bridge && \
	rm -rf dist && \
	VERSION=$$(cat VERSION) && \
	xgo --out=hrequests-cgo-$$VERSION -buildmode=c-shared --dest=./dist .

vermin:
	vermin --eval-annotations --target=3.8 --violations .

publish:
	find ./hrequests/bin -type f ! -name "*.txt" ! -name "*.py" -exec rm -v {} \;
	vermin . --eval-annotations --target=3.8 --violations hrequests/ || exit 1
	rm -rf ./dist
	python -m build
	twine check dist/*
	@read -p "Confirm publish? [y/N] " ans && [ $${ans:-N} = y ]
	twine upload dist/*
