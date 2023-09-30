set /p ver=<VERSION

xgo --out=hrequests-cgo-%ver% -buildmode=c-shared --dest=./dist .