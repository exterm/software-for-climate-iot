.PHONY: deploy shell clean install-libraries

DEVICE_PATH = /run/media/philip/CIRCUITPY
DEVICE_ADDRESS = /dev/ttyACM0

deploy: dist/settings.toml $(patsubst src/%, $(DEVICE_PATH)/%, $(wildcard src/*))
	@echo "Deployed to $(DEVICE_PATH)"

$(DEVICE_PATH)/%: dist/%
	cp -r $< $@

shell:
	screen $(DEVICE_ADDRESS) 115200


dist/settings.toml: src/settings.toml SECRET_SETTINGS
	@mkdir -p dist
	@cp src/settings.toml dist/settings.toml
	@echo >> dist/settings.toml
	@echo "# Secret settings" >> dist/settings.toml
	@cat SECRET_SETTINGS >> dist/settings.toml

dist/%: src/%
	@mkdir -p dist
	cp $< $@

clean:
	@echo "cleaning"
	@rm -rf dist
	@find $(DEVICE_PATH) -mindepth 1 -maxdepth 1 -type f -not -name "boot_out.txt" -delete
	@echo "done"

install-libraries:
	circup install -r requirements.txt
