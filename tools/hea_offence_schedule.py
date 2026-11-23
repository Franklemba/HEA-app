"""HEA Schedule of Offences (Disciplinary and Grievance Procedure Code, June 2016, section 5.8.16).

Writes the Offence Category, Offence Master and Offence Sanction Matrix fixtures for the hea app.
Usage: python3 tools/hea_offence_schedule.py   (from apps/hea)

Each offence: (number, category, short name, code text, [1st, 2nd, 3rd, 4th breach penalty]).
Penalties are verbatim from the Code; None where the Code gives N/A or nothing.
"""

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "hea" / "fixtures"
REFERENCE = "Disciplinary and Grievance Procedure Code (2016), 5.8.16"

TIME = "Time Keeping and Attendance"
PERFORMANCE = "Work Performance"
CONDUCT = "Indiscipline and Disorderly Conduct"
PROPERTY = "Authority Property and Resources"
DISHONESTY = "Dishonesty, Fraud and Corruption"
VEHICLES = "Motor Vehicles"
HARASSMENT = "Sexual Harassment"
IT = "Information Technology"

VW, RW, FW = "Verbal Warning", "Recorded Warning", "Final Warning"

OFFENCES = [
	("1", TIME, "Lateness, poor time keeping or leaving early",
		"Lateness or poor time keeping, leaving early", [VW, RW, FW, "Discharge"]),
	("2", TIME, "Extended or unauthorised breaks",
		"Extended or unauthorised breaks during working hours without reasonable justification or permission.",
		[VW, RW, FW, "Discharge"]),
	("3", PERFORMANCE, "Unsatisfactory work performance",
		"Unsatisfactory work performance as evidenced by sub-standard performance, carelessness, unsatisfactory work.",
		[VW, RW, "Final Warning, Demotion", "Discharge"]),
	("4", TIME, "Absence from work without excuse or permission",
		"Absence from work without reasonable excuse or prior permission during a working day.",
		[VW, RW, FW, "Discharge"]),
	("5", TIME, "Desertion (absence for ten or more consecutive days)",
		"Absence from work without permission and justification for ten or more consecutive days.",
		["Will be deemed as desertion, summary dismissal", None, None, None]),
	("6", TIME, "Abandoning place of work during working hours",
		"Abandoning one's place of work during working hours.", [RW, FW, "Dismissal", None]),
	("7", TIME, "Loitering, loafing, laziness or malingering",
		"Loitering/loafing on job/laziness/malingering/ inefficiency, lack of effort", [VW, RW, FW, "Dismissal"]),
	("8", TIME, "Sleeping on duty",
		"Sleeping on Duty as witnessed by 2 persons",
		["Recorded Warning with suspension without pay for 5 days.", FW, "Dismissal", None]),
	("9", CONDUCT, "Indiscipline, insubordination or failure to obey lawful instructions",
		"Indiscipline/Insubordination or failure to obey lawful instructions shown by attitude towards work.",
		["Final Warning and 10 days suspension without pay.", "Discharge", None, None]),
	("10", CONDUCT, "Unauthorised press statement on Authority matters",
		"Unauthorised press statement on Authority matters.",
		["Final Warning and 5 days suspension without pay.", "Dismissal", None, None]),
	("11", PROPERTY, "Damage to or loss of Authority property or resources",
		"Damage to or loss of Authority property or resources without acceptable reason.",
		["Recorded Warning and 100% Surcharge", "Final Warning and Surcharge", "Dismissal", None]),
	("12", PROPERTY, "Unauthorised use or misuse of Authority property",
		"Unauthorised/Misuse of Authority property including vehicles.",
		["Recorded Warning and 100% Surcharge", "Dismissal", None, None]),
	("13", PROPERTY, "Outright carelessness, malicious damage or sabotage",
		"Outright carelessness, malicious damage to property and vehicles, sabotage",
		["Dismissal and repayment", None, None, None]),
	("14", CONDUCT, "Alcohol or intoxicating drugs at work",
		"Taking alcoholic drinks or intoxicating drugs on Authority and/or during working hours as evidenced by at least two persons.",
		["Dismissal", None, None, None]),
	("15", PROPERTY, "Found with Authority property without authority",
		"Being found with Authority property without authority", ["Dismissal", None, None, None]),
	("16", DISHONESTY, "Conspiracy to defraud or remove Authority property",
		"Conspiracy to defraud or remove Authority property without authority.", ["Dismissal", None, None, None]),
	("17", DISHONESTY, "Misappropriation of Authority funds",
		"Misappropriation of Authority funds.", ["Dismissal", None, None, None]),
	("18", CONDUCT, "Breach of Authority policy, rules and regulations",
		"Breach of policy rules and regulations as stipulated in all operating Authority manuals.",
		[FW, "Discharge", None, None]),
	("19", DISHONESTY, "Theft or fraud", "Theft/Fraud (as evidenced)", ["Dismissal", None, None, None]),
	("20", DISHONESTY, "Forgery", "Forgery (as evidenced)", ["Dismissal", None, None, None]),
	("21", DISHONESTY, "Uttering", "Uttering (as evidenced)", ["Dismissal", None, None, None]),
	("22", DISHONESTY, "Dishonest conduct", "Dishonest conduct (as evidenced)", ["Dismissal", None, None, None]),
	("23", DISHONESTY, "Corruption", "Corruption (as evidenced)", ["Dismissal", None, None, None]),
	("24", DISHONESTY, "Bribery", "Bribery (as evidenced)", ["Dismissal", None, None, None]),
	("25", CONDUCT, "Assault, intimidation or threatening violence",
		"Assault and/or intimidation threatening violence/ Starting a fight (a physical combat) disorderly behaviours "
		"at workplace or on Authority business.",
		["Dismissal", None, None, None]),
	("26", CONDUCT, "Fighting or disorderly behaviour",
		"Fighting or disorderly behaviour.", [RW, FW, "Dismissal", None]),
	("27", CONDUCT, "Inciting, riotous behaviour or unconstitutional strike",
		"Inciting, riotous behaviour or unconstitutional strike.", ["Dismissal", None, None, None]),
	("28", CONDUCT, "Conduct bringing the Authority into disrepute",
		"Conduct or position likely to bring disrepute to the Authority", [FW, "Dismissal", None, None]),
	("29", VEHICLES, "Failure to obtain third-party details and police report after an accident",
		"Failure to collect information commitment from third party at fault and police report for purposes of "
		"collecting insurance or payment towards accident repair costs.",
		["Warning letter and surcharge of 1 month base salary", "Second Warning 100% surcharge",
			"Final Warning plus 100% surcharge", "Withdrawal of vehicle"]),
	("30", VEHICLES, "Blameworthy minor motor vehicle accident",
		"Blameworthy minor motor vehicle accidents where potential for loss and actual damage is minimal.",
		["Warning letter plus 20% surcharge.", "Second Warning plus surcharge of 50% of repair costs.",
			"Final warning, surcharge of 100% of repair costs and 1 month suspension from driving Authority vehicle",
			"Dismissal or withdrawal of vehicle"]),
	("31", VEHICLES, "Blameworthy motor vehicle accident with huge loss",
		"Blameworthy motor vehicle accidents resulting from carelessness where huge losses and potential for huge "
		"losses, including life has been determined.",
		["Final Warning plus surcharge of 50% or repair costs and/or 1 month suspension from driving Authority vehicle",
			"Dismissal", None, None]),
	("32", PROPERTY, "Gross negligence causing damage to or loss of property",
		"Gross Negligence resulting in Damage to or loss of company property depending on seriousness of offence.",
		["Recorded Warning and Surcharge 50%", "Final Warning and Surcharge 100%", "Dismissal", None]),
	("33.1", HARASSMENT, "Sexual advances",
		"Sexual Advances - unsolicited sexual comments, suggestions, gestures, unwarranted physical contact which one "
		"finds offensive or uncomfortable in a work environment.",
		["Written warning", "Final written warning", "Dismissal", None]),
	("33.2", HARASSMENT, "Sexual imposition",
		"Sexual imposition - meaning the touching of another person's erogenous area (thigh, genitals, buttock, "
		"public region, or female breast)",
		["Severe warning", "Final written warning", "Dismissal", None]),
	("33.3", HARASSMENT, "Sexual bribery",
		"Sexual bribery - sexual relationship with an employer or superior is made an explicit or implied condition "
		"for obtaining/retaining employment or its benefits",
		["Final written warning", "Dismissal", None, None]),
	("33.4", HARASSMENT, "Rape",
		"Rape - is a type of sexual assault usually involving sexual intercourse or other forms of sexual penetration "
		"perpetrated against a person without that person's consent.",
		["Dismissal", None, None, None]),
	("34.1", IT, "Unauthorised access to computer program or data",
		"An Unauthorised entry or access to Computer Program or data", [FW, "Dismissal", None, None]),
	("34.2", IT, "Unauthorised obstruction of computer program or software installation",
		"An unauthorised Obstruction of Computer Program or software Installation", [FW, "Dismissal", None, None]),
	("34.3", IT, "Unauthorised disclosure of computer access codes",
		"An unauthorised Disclosure, giving or Receiving of access code to a computer program or data",
		[FW, "Dismissal", None, None]),
	("34.4", IT, "Unauthorised modification of computer program, software or data",
		"An unauthorised modification to a Computer program, Software or data", ["Dismissal", None, None, None]),
	("34.5", IT, "Deliberately causing a computer to cease to function",
		"Deliberately Causing a Computer to cease to function (to crush)", ["Dismissal", None, None, None]),
	("34.6", IT, "Posting detrimental information on social media",
		"Posting and or causing to be posted onto the Social media information or data that is detrimental to the "
		"Authority or puts the name of the Authority and or its operations and dealings into disrepute",
		["Dismissal", None, None, None]),
	("34.7", IT, "Visiting or downloading prohibited sites on Authority IT equipment",
		"Visiting and or downloading prohibited sites, such as pornographic sites during working hours on the "
		"Company IT Equipment (Personal Computers, laptops and other IT Tools provided by the Authority",
		[RW, FW, "Dismissal", None]),
]

BREACHES = ["1st Breach", "2nd Breach", "3rd Breach", "4th Breach"]

# Sanction levels, least to most severe; the scripts work from these rather than the Code's free wording.
SANCTION_LEVELS = [
	"Verbal Warning",
	"Written Warning",
	"Final Warning",
	"Demotion",
	"Withdrawal of Vehicle",
	"Discharge",
	"Dismissal",
	"Summary Dismissal",
]


def sanction_level(penalty):
	p = penalty.lower()
	if "summary dismissal" in p:
		return "Summary Dismissal"
	if p.startswith("dismissal"):
		return "Dismissal"
	if p.startswith("discharge"):
		return "Discharge"
	if p.startswith("withdrawal of vehicle"):
		return "Withdrawal of Vehicle"
	if "demotion" in p:
		return "Demotion"
	if p.startswith("final"):
		return "Final Warning"
	if p.startswith("verbal"):
		return "Verbal Warning"
	# Recorded / Written / Severe / Second warning, Warning letter
	return "Written Warning"


def code(number):
	major, _, minor = number.partition(".")
	return f"HEA-{int(major):02d}" + (f".{minor}" if minor else "")


def build():
	categories, masters, matrix = [], [], []
	for number, category, name, text, penalties in OFFENCES:
		if category not in {c["name"] for c in categories}:
			categories.append(
				{"doctype": "Offence Category", "name": category, "offence_category": category, "docstatus": 1}
			)
		masters.append(
			{
				"doctype": "Offence Master",
				"name": name,
				"offence_name": name,
				"offence_code": code(number),
				"offence_category": category,
				"definition": text,
				"reference_section": f"{REFERENCE} ({number})",
				"docstatus": 1,
			}
		)
		for breach, penalty in zip(BREACHES, penalties):
			if not penalty:
				continue
			matrix.append(
				{
					"doctype": "Offence Sanction Matrix",
					"name": f"OSM-{len(matrix) + 1:04d}",
					"offence": name,
					"offence_code": code(number),
					"offence_name": name,
					"offence_category": category,
					"breach_number": breach,
					"prescribed_sanction": penalty.rstrip("."),
					"sanction_level": sanction_level(penalty),
					"reference_table": f"{REFERENCE} ({number})",
					"docstatus": 1,
				}
			)
	return categories, masters, matrix


if __name__ == "__main__":
	categories, masters, matrix = build()
	assert len({m["name"] for m in masters}) == len(masters), "offence names must be unique"
	for key, docs in (
		("offence_category", categories),
		("offence_master", masters),
		("offence_sanction_matrix", matrix),
	):
		(FIXTURES / f"{key}.json").write_text(json.dumps(docs, indent=1, ensure_ascii=False) + "\n")
	print(f"{len(categories)} categories, {len(masters)} offences, {len(matrix)} sanction rows")
