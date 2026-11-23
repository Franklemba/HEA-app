from hea.registry.mail_register import execute as register


def execute(filters=None):
	return register("Incoming", filters)
