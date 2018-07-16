#!/usr/bin/python
#coding=utf-8


import requests
import re
import subprocess
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.error import BadRequest
from telegram import ParseMode
from PandaRPC import PandaRPC, Wrapper as RPCWrapper
from HelperFunctions import *
import sys, traceback
import logging
logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO
)

config = load_file_json("config.json")
_lang = "fr" # ToDo: Per-user language
strings = Strings("strings.json")


# Constants
__wallet_rpc = RPCWrapper(PandaRPC(config["rpc-uri"], (config["rpc-user"], config["rpc-psw"])))


# ToDo: Don't forget to write the strings in strings.json (they are actually empty)
def cmd_start(bot, update, args):
	"""Reacts when /start is sent to the bot."""
	if update.effective_chat.type == "private":
		# Check for deep link
		if len(args) > 0:
			if args[0].lower() == "about":
				cmd_about(bot, update)
			elif args[0].lower() == "help":
				cmd_help(bot, update)
			else:
				update.message.reply_text(
					strings.get("error_bad_deep_link", _lang),
					quote=True,
					parse_mode=ParseMode.MARKDOWN,
					disable_web_page_preview=True
				)
		else:
			update.message.reply_text(
				strings.get("welcome", _lang),
				quote=True,
				parse_mode=ParseMode.MARKDOWN,
				disable_web_page_preview=True
			)


def cmd_about(bot, update):
	if update.effective_chat is None:
		_chat_type = "private"
	elif update.effective_chat.type == "private":
		_chat_type = "private"
	else:
		_chat_type = "group"
	#
	if _chat_type == "private":
		# Check if callback
		try:
			if update.callback_query.data is not None:
				update.callback_query.answer(strings.get("about", _lang))
		except:
			pass
		bot.send_message(
			chat_id=update.effective_chat.id,
			text=strings.get("about", _lang),
			parse_mode=ParseMode.MARKDOWN,
			disable_web_page_preview=True
		)
	else:
		# ToDo: Button
		update.message.reply_text(
			"%s\n[About %s](https://telegram.me/%s?start=about)" % (
				strings.get("about_public", _lang), config["telegram-botname"], config["telegram-botname"]
			),
			parse_mode=ParseMode.MARKDOWN,
			disable_web_page_preview=True
		)
	return True


def cmd_help(bot, update):
	if update.effective_chat is None:
		_chat_type = "private"
	elif update.effective_chat.type == "private":
		_chat_type = "private"
	else:
		_chat_type = "group"
	#
	if _chat_type == "private":
		# Check if callback
		try:
			if update.callback_query.data is not None:
				update.callback_query.answer(strings.get("help", _lang))
		except:
			pass
		bot.send_message(
			chat_id=update.effective_chat.id,
			text=strings.get("help", _lang),
			parse_mode=ParseMode.MARKDOWN,
			disable_web_page_preview=True
		)
	else:
		# ToDo: Button
		update.message.reply_text(
			"%s\n[Help!](https://telegram.me/%s?start=help)" % (strings.get("help_public", _lang), config["telegram-botname"]),
			parse_mode=ParseMode.MARKDOWN,
			disable_web_page_preview=True
		)
	return True


def deposit(bot, update):
	"""
	This commands works only in private.
	If the user has no address, a new account is created with his Telegram user ID (str)
	"""
	if update.effective_chat is None:
		_chat_type = "private"
	elif update.effective_chat.type == "private":
		_chat_type = "private"
	else:
		_chat_type = "group"
	# Only show deposit address if it's a private conversation with the bot
	if _chat_type == "private":
		_user_id = '@' + update.effective_user.username.lower()
		if _user_id is None: _user_id = str(update.effective_user.id)
		_address = None
		_rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
		if not _rpc_call["success"]:
			print("Error during RPC call.")
		else:
			if _rpc_call["result"]["error"] is not None:
				print("Error: %s" % _rpc_call["result"]["error"])
			else:
				# Check if user already has an address. This will prevent creating another address if user has one
				_addresses = _rpc_call["result"]["result"]
				if len(_addresses) == 0:
					# Done: User has no address, request a new one (2018-07-16)
					_rpc_call = __wallet_rpc.getaccountaddress(_user_id)
					if not _rpc_call["success"]:
						print("Error during RPC call.")
					else:
						if _rpc_call["result"]["error"] is not None:
							print("Error: %s" % _rpc_call["result"]["error"])
						else:
							_address = _rpc_call["result"]["result"]
				else:
					_address = _addresses[0]
				# ToDo: Can it happen that a user gets more than juan address? Verify.
				if _address is not None:
					update.message.reply_text(
						text="%s `%s`" % (strings.get("user_address", _lang), _address),
						quote=True,
						parse_mode=ParseMode.MARKDOWN,
						disable_web_page_preview=True
					)


# Done: Give balance only if a private chat (2018-07-15)
# Done: Remove WorldCoinIndex (2018-07-15)
# ToDo: Add conversion
def balance(bot, update):
	if update.effective_chat is None:
		_chat_type = "private"
	elif update.effective_chat.type == "private":
		_chat_type = "private"
	else:
		_chat_type = "group"
	# Only show balance if it's a private conversation with the bot
	if _chat_type == "private":
		# See issue #2 (https://github.com/DarthJahus/PandaTip-Telegram/issues/2)
		_user_id = '@' + update.effective_user.username.lower()
		if _user_id is None: _user_id = str(update.effective_user.id)
		# get address of user
		_rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
		if not _rpc_call["success"]:
			print("Error during RPC call: %s" % _rpc_call["message"])
		elif _rpc_call["result"]["error"] is not None:
			print("Error: %s" % _rpc_call["result"]["error"])
		else:
			_addresses = _rpc_call["result"]["result"]
			if len(_addresses) == 0:
				# User has no address, ask him to create one
				update.message.reply_text(
					text=strings.get("user_no_address", _lang),
					quote=True
				)
			else:
				# ToDo: Handle the case when user has many addresses?
				# ToDo: Maybe if something really weird happens and user ends up having more, we can calculate his balance.
				# ToDo: This way, when asking for address (/deposit), we can return the first one.
				_address = _addresses[0]
				_rpc_call = __wallet_rpc.getbalance(_address)
				if not _rpc_call["success"]:
					print("Error during RPC call.")
				elif _rpc_call["result"]["error"] is not None:
					print("Error: %s" % _rpc_call["result"]["error"])
				else:
					_balance = float(_rpc_call["result"]["result"])
					update.message.reply_text(
						text="%s\n`%.0f PND`" % (strings.get("user_balance", _lang), _balance),
						parse_mode=ParseMode.MARKDOWN,
						quote=True
					)


# Done: Rewrite the whole logic; use tags instead of parsing usernames (2018-07-15)
# ToDo: Allow private tipping if the user can be tagged (@username available) (Probably works, now)
def tip(bot, update):
	"""
	/tip <user> <amount>
	/tip u1 u2 u3 ... v1 v2 v3 ...
	/tip u1 v1 u2 v2 u3 v3 ...
	"""
	#
	# Get recipients and values
	_message = update.effective_message.text
	_modifier = 0
	_recipients = {}
	for entity in update.effective_message.entities:
		if entity.type == "text_mention":
			# UserId is unique
			_username = entity.user.name
			if str(entity.user.id) not in _recipients:
				_recipients[str(entity.user.id)] = (_username, entity.offset, entity.length)
		elif entity.type == "mention":
			# _username starts with @
			# _username is unique
			_username = update.effective_message.text[entity.offset:(entity.offset+entity.length)].lower()
			if _username not in _recipients:
				_recipients[_username] = (_username, entity.offset, entity.length)
		_part = _message[:entity.offset-_modifier]
		_message = _message[:entity.offset-_modifier] + _message[entity.offset+entity.length-_modifier:]
		_modifier = entity.offset+entity.length-len(_part)
	print(_recipients)
	_amounts = _message.split()
	# check if amounts are all convertible to float
	_amounts_float = []
	try:
		for _amount in _amounts:
			_amounts_float.append(float(_amount))
	except:
		_amounts_float = []
	# Make sure number of recipients is the same as number of values
	if len(_amounts_float) != len(_recipients):
		update.message.reply_text(
			text="There was an error in your tip. Number of recipients needs to be the same as the number of amounts.",
			quote=True
		)
	else:
		#
		# Check if user has enough balance
		_user_id = '@' + update.effective_user.username.lower()
		if _user_id is None: _user_id = str(update.effective_user.id)
		# get address of user
		_rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
		if not _rpc_call["success"]:
			print("Error during RPC call: %s" % _rpc_call["message"])
		elif _rpc_call["result"]["error"] is not None:
			print("Error: %s" % _rpc_call["result"]["error"])
		else:
			_addresses = _rpc_call["result"]["result"]
			if len(_addresses) == 0:
				# User has no address, ask him to create one
				update.message.reply_text(
					text=strings.get("user_no_address", _lang),
					quote=True
				)
			else:
				# ToDo: Maybe handle many addresses
				_address = _addresses[0]
				# Get user's balance
				_rpc_call = __wallet_rpc.getbalance(_address)
				if not _rpc_call["success"]:
					print("Error during RPC call.")
				elif _rpc_call["result"]["error"] is not None:
					print("Error: %s" % _rpc_call["result"]["error"])
				else:
					_balance = float(_rpc_call["result"]["result"])
					# Now, finally, check if user has enough funds (includes tx fee)
					if sum(_amounts_float) > _balance - max(1, int(len(_recipients)/3)):
						update.message.reply_text(
							text="%s `%.0f PND`" % (strings.get("user_no_funds", _lang), sum(_amounts_float)),
							quote=True
						)
					else:
						# Now create the {recipient_id: amount} dictionary
						i = 0
						_tip_dict = {}
						for _recipient in _recipients:
							if _recipient[0] == '@':
								# ToDo: Get the id (actually not possible (Bot API 3.6, Feb. 2018)
								# See issue #2 (https://github.com/DarthJahus/PandaTip-Telegram/issues/2)
								# Using the @username
								# Done: When requesting a new address, if user has a @username, then use that username (2018-07-16)
								# Problem: If someone has no username, then later creates one, he loses access to his account
								# Done: Create a /scavenge command that allows people who had UserID to migrate to UserName (2018-07-16)
								_recipient_id = _recipient
							else:
								_recipient_id = _recipient
							# Check if recipient has an address (required for .sendmany()
							_rpc_call = __wallet_rpc.getaddressesbyaccount(_recipient_id)
							if not _rpc_call["success"]:
								print("Error during RPC call.")
							elif _rpc_call["result"]["error"] is not None:
								print("Error: %s" % _rpc_call["result"]["error"])
							else:
								_address = None
								_addresses = _rpc_call["result"]["result"]
								if len(_addresses) == 0:
									# ToDo: recipient has no address, create one
									_rpc_call = __wallet_rpc.getaccountaddress(_recipient_id)
									if not _rpc_call["success"]:
										print("Error during RPC call.")
									elif _rpc_call["result"]["error"] is not None:
										print("Error: %s" % _rpc_call["result"]["error"])
									else:
										_address = _rpc_call["result"]["result"]
								else:
									# Recipient has an address, we don't need to create one for him
									_address = _addresses[0]
							if _address is not None:
								# Because recipient has an address, we can add him to the dict
								_tip_dict[_recipient_id] = _amounts_float[i]
							i += 1
						#
						# Done: replace .move by .sendfrom or .sendmany (2018-07-16) 
						# sendfrom <from address or account> <receive address or account> <amount> [minconf=1] [comment] [comment-to]
						# and
						# sendmany <from address or account> {receive address or account:amount,...} [minconf=1] [comment]
						_rpc_call = __wallet_rpc.sendmany(_user_id, _tip_dict)
						if not _rpc_call["success"]:
							print("Error during RPC call.")
						elif _rpc_call["result"]["error"] is not None:
							print("Error: %s" % _rpc_call["result"]["error"])
						else:
							_tx = _rpc_call["result"]["result"]
							_suppl = ""
							if len(_tip_dict) != len(_recipients):
								_suppl = "\n\n_%s_" % strings.get("missing_tip_recipient", _lang)
							update.message.reply_text(
								text = "%s %s\n%s\n\n[tx %s](%s)%s" % (
									update.effective_user.name,
									strings.get("success_tip", _lang),
									(("\n- *%s* with `%.0f PND`" % (_recipient, _tip_dict[_recipient])) for _recipient in _tip_dict),
									_tx[:4] + "..." + _tx[-4:],
									"https://chainz.cryptoid.info/pnd/tx.dws?" + _tx,
									_suppl
								),
								quote=True,
								parse_mode=ParseMode.MARKDOWN,
								disable_web_page_preview=True
							)


# Done: Revamp withdraw() function (2018-07-16)
def withdraw(bot, update, args):
	"""
	Withdraw to an address. Works only in private.
	"""
	if update.effective_chat is None:
		_chat_type = "private"
	elif update.effective_chat.type == "private":
		_chat_type = "private"
	else:
		_chat_type = "group"
	#
	if _chat_type == "private":
		_amount = None
		_recipient = None
		if len(args) == 2:
			try:
				_amount = int(args[1])
				_recipient = args[0]
			except:
				try:
					_amount = int(args[0])
					_recipient = args[1]
				except:
					pass
		else:
			update.message.reply_text(
				text="Too few or too many arguments for this command.",
				quote=True
			)
		if _amount is not None and _recipient is not None:
			_user_id = '@' + update.effective_user.username.lower()
			if _user_id is None: _user_id = str(update.effective_user.id)
			# get address of user
			_rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
			if not _rpc_call["success"]:
				print("Error during RPC call: %s" % _rpc_call["message"])
			elif _rpc_call["result"]["error"] is not None:
				print("Error: %s" % _rpc_call["result"]["error"])
			else:
				_addresses = _rpc_call["result"]["result"]
				if len(_addresses) == 0:
					# User has no address, ask him to create one
					update.message.reply_text(
						text=strings.get("user_no_address", _lang),
						quote=True
					)
				else:
					_address = _addresses[0]
					_rpc_call = __wallet_rpc.getbalance(_address)
					if not _rpc_call["success"]:
						print("Error during RPC call.")
					elif _rpc_call["result"]["error"] is not None:
						print("Error: %s" % _rpc_call["result"]["error"])
					else:
						_balance = float(_rpc_call["result"]["result"])
						if _balance < _amount + 5:
							update.message.reply_text(
								text="%s `%.0f PND`" % (strings.get("user_no_funds", _lang), _amount+5),
								quote=True,
								parse_mode=ParseMode.MARKDOWN
							)
						else:
							# Withdraw
							_rpc_call = __wallet_rpc.sendfrom(_user_id, _recipient, _amount)
							if not _rpc_call["success"]:
								print("Error during RPC call.")
							elif _rpc_call["result"]["error"] is not None:
								print("Error: %s" % _rpc_call["result"]["error"])
							else:
								_tx = _rpc_call["result"]["result"]
								update.message.reply_text(
									text="%s\n[tx %s](%s)" % (
										strings.get("success_withdraw", _lang),
										_tx[:4]+"..."+_tx[-4:],
										"https://chainz.cryptoid.info/pnd/tx.dws?" + _tx
									),
									quote=True,
									parse_mode=ParseMode.MARKDOWN,
									disable_web_page_preview=True
								)


def scavenge(bot, update):
	if update.effective_chat is None:
		_chat_type = "private"
	elif update.effective_chat.type == "private":
		_chat_type = "private"
	else:
		_chat_type = "group"
	# Only if it's a private conversation with the bot
	if _chat_type == "private":
		_username = '@' + update.effective_user.username.lower()
		if _username is None:
			update.message.reply_text(
				text="Sorry, this command is not for you.",
				quote=True
			)
		else:
			_user_id = str(update.effective_user.id)
			# Done: Check balance of UserID (2018-07-16)
			# get address of user
			_rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
			if not _rpc_call["success"]:
				print("Error during RPC call: %s" % _rpc_call["message"])
			elif _rpc_call["result"]["error"] is not None:
				print("Error: %s" % _rpc_call["result"]["error"])
			else:
				_addresses = _rpc_call["result"]["result"]
				if len(_addresses) == 0:
					update.message.reply_text(
						text="%s (`%s`)" % (strings.get("scavenge_no_address", _lang), _user_id),
						quote=True,
					)
				else:
					_address = _addresses[0]
					_rpc_call = __wallet_rpc.getbalance(_address)
					if not _rpc_call["success"]:
						print("Error during RPC call.")
					elif _rpc_call["result"]["error"] is not None:
						print("Error: %s" % _rpc_call["result"]["error"])
					else:
						_balance = float(_rpc_call["result"]["result"])
						# Done: Move balance from UserID to @username if balance > 5 (2018-07-16)
						if int(_balance) <= 5:
							update.message.reply_text(
								text="Your previous account (`%s`) is empty. Nothing to scavenge." % _user_id,
								parse_mode=ParseMode.MARKDOWN,
								quote=True
							)
						else:
							# Need to make sure there is an account for _username
							_rpc_call = __wallet_rpc.getaddressesbyaccount(_username)
							if not _rpc_call["success"]:
								print("Error during RPC call: %s" % _rpc_call["message"])
							elif _rpc_call["result"]["error"] is not None:
								print("Error: %s" % _rpc_call["result"]["error"])
							else:
								_address = None
								_addresses = _rpc_call["result"]["result"]
								if len(_addresses) == 0:
									# Create an address for user (_username)
									_rpc_call = __wallet_rpc.getaccountaddress(_username)
									if not _rpc_call["success"]:
										print("Error during RPC call.")
									elif _rpc_call["result"]["error"] is not None:
										print("Error: %s" % _rpc_call["result"]["error"])
									else:
										_address = _rpc_call["result"]["result"]
								else:
									_address = _addresses[0]
								if _address is not None:
									# Move the funds from UserID to Username
									# ToDo: Make the fees consistent
									_rpc_call = __wallet_rpc.sendfrom(_user_id, _address, _balance-5)
									if not _rpc_call["success"]:
										print("Error during RPC call.")
									elif _rpc_call["result"]["error"] is not None:
										print("Error: %s" % _rpc_call["result"]["error"])
									else:
										_tx = _rpc_call["result"]["result"]
										update.message.reply_text(
											text="%s (`%s`)\n%s `%.0f PND`\n[tx %s](%s)" % (
												strings.get("success_scavenge_1", _lang),
												_user_id,
												strings.get("success_scavenge_2", _lang),
												_balance-5,
												_tx[:4]+"..."+_tx[-4:],
												"https://chainz.cryptoid.info/pnd/tx.dws?" + _tx,
											),
											quote=True,
											parse_mode=ParseMode.MARKDOWN,
											disable_web_page_preview=True
										)


# ToDo: Revamp functions bellow


def price(bot,update):
	# ToDo:
	pass


def hi(bot,update):
	user = update.message.from_user.username
	bot.send_message(chat_id=update.message.chat_id, text="Hello @{0}, how are you doing today?".format(user))


def moon(bot,update):
	bot.send_message(chat_id=update.message.chat_id, text="Moon mission inbound!")


def market_cap(bot,update):
	# ToDo:
	pass


if __name__ == "__main__":
	updater = Updater(token=config["telegram-token"])
	dispatcher = updater.dispatcher
	# TGBot commands
	dispatcher.add_handler(CommandHandler('start', cmd_start, pass_args=True))
	dispatcher.add_handler(CommandHandler('help', cmd_help))
	dispatcher.add_handler(CommandHandler('about', cmd_about))
	# Funny commands
	dispatcher.add_handler(CommandHandler('moon', moon))
	dispatcher.add_handler(CommandHandler('hi', hi))
	# Tipbot commands
	dispatcher.add_handler(CommandHandler('tip', tip))
	dispatcher.add_handler(CommandHandler('withdraw', withdraw, pass_args=True))
	dispatcher.add_handler(CommandHandler('deposit', deposit))
	dispatcher.add_handler(CommandHandler('address', deposit)) # alias for /deposit
	dispatcher.add_handler(CommandHandler('balance', balance))
	dispatcher.add_handler(CommandHandler("scavenge", scavenge))
	# Conversion commands
	dispatcher.add_handler(CommandHandler('marketcap', marketcap))
	dispatcher.add_handler(CommandHandler('price', price))
	updater.start_polling()
