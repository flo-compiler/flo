LDFLAGS=-L/usr/lib/llvm/lib -lLLVM-15

FLO_INSTALL_PATH=/usr/local/flo

TMP_DIR=/tmp

define compile_and_link_fc
	$(1) src/main.flo --emit obj -o $(1).o -O 3 -I ./lib/
	$(CC) -no-pie $(1).o $(TMP_DIR)/llvm-bind.so $(LDFLAGS) -o $(2)
endef

all: flo

flo: helper
	$(CC) -c src/llvm/FloLLVMBind.cpp -o $(TMP_DIR)/llvm-bind.so
	$(call compile_and_link_fc,$(TMP_DIR)/stage0,$(TMP_DIR)/stage1)
	$(call compile_and_link_fc,$(TMP_DIR)/stage1,$@)

helper:
	$(CC) bootstrap/helper.c $(LDFLAGS) -o helper
	./helper
	mv stage0.o $(TMP_DIR)/	

check:
	./runtests.py

install:
	sudo mkdir -p $(FLO_INSTALL_PATH)
	sudo cp -f flo $(FLO_INSTALL_PATH)
	sudo cp -r lib $(FLO_INSTALL_PATH)
	sudo ln -f $(FLO_INSTALL_PATH)/flo /usr/bin/flo

clean:
	rm -rf flo helper
