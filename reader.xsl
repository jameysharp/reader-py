<?xml version="1.0"?>

<xsl:stylesheet
    version="1.0"
    exclude-result-prefixes="atom"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:output method="html" omit-xml-declaration="yes" indent="no"/>

<xsl:param name="iconpath" select="'https://www.comic-rocket.com/media/img/'"/>

<xsl:template match="/">
<html>
<head>
	<meta name="generator" content="https://github.com/jameysharp/css-feed-reader" />
	<meta name="viewport" content="width=device-width" />
	<title><xsl:value-of select="//atom:feed/atom:title"/></title>
	<style>
		body {
			position: absolute;
			width: 100%;
			height: 100%;
			margin: 0;
			display: flex;
			flex-direction: column;
		}
		#top, #left {
			margin: 0;
			padding: 0;
			box-sizing: border-box;
		}
		#top {
			width: 100%;
			background-color: black;
			color: white;
			display: flex;
			align-items: center;
			flex-shrink: 0;
			flex-grow: 0;
		}
		#top > * {
			flex-shrink: 0;
			flex-grow: 0;
		}
		#top label.preload {
			background-color: #4A1600;
			background-position: center;
			background-repeat: no-repeat;
			width: 2.2em;
			height: 2.2em;
		}
		#top label.preload[for] {
			background-color: #93320C;
		}
		#top label.preload[for]:hover {
			background-color: #4A1600;
		}
		label.before {
			background-image: url('<xsl:value-of select="$iconpath"/>icon-prevpage.png');
		}
		label.after {
			background-image: url('<xsl:value-of select="$iconpath"/>icon-nextpage.png');
		}
		#top > .title {
			flex-grow: 1;
			flex-shrink: 1;
			text-align: center;
			overflow: hidden;
			white-space: nowrap;
			text-overflow: ellipsis;
			margin: 0 0.5ex;
		}
		time {
			color: #DDD;
			font-size: 80%;
			display: block;
		}
		#left time {
			color: #555;
		}
		#left ul {
			padding: 0;
			margin: 1ex;
			list-style: none;
		}
		#left li {
			margin-bottom: 1ex;
		}
		#left {
			position: absolute;
			top: 0;
			left: -30%;
			height: 100%;
			background-color: #EEC;
			border: 2px solid black;
			overflow: auto;
			visibility: hidden;
			width: 30%;
			transition-property: visibility, left;
			transition-duration: 100ms;
		}
		#expand-sidebar:checked ~ #left {
			visibility: visible;
			left: 0;
		}
		#expand-sidebar-btn {
			padding: 3px;
			background-color: #EEC;
			color: black;
			font-size: 120%;
			margin-right: 1em;
			transition-property: margin;
			transition-duration: 100ms;
		}
		#expand-sidebar:checked ~ #top #expand-sidebar-btn {
			margin-left: 30%;
		}
		#content {
			flex-grow: 1;
			display: flex;
		}
		#content > * {
			display: flex;
		}
		#content * {
			flex-grow: 1;
		}
		iframe {
			margin: 0;
			padding: 0;
			border: 0;
		}
		input, .preload {
			display: none;
		}<xsl:apply-templates select="//atom:entry" mode="style" />
	</style>
</head>
<body>
	<input type="checkbox" id="expand-sidebar" />
	<xsl:apply-templates select="//atom:entry" mode="radio" />

	<div id="top">
		<label for="expand-sidebar" id="expand-sidebar-btn">&#187;</label>
		<xsl:apply-templates select="//atom:entry" mode="top" />
	</div>

	<div id="content">
		<noscript id="preloadContent">
		<xsl:apply-templates select="//atom:entry" mode="iframe" />
		</noscript>
	</div>

	<div id="left">
		<ul>
		<xsl:apply-templates select="//atom:entry" mode="left" />
		</ul>
	</div>

	<!-- progressive enhancements -->
	<script><xsl:text>
		(function() {
			var iframes = document.createElement("div");
			function preload(pageid, src) {
				// get the radio button and create a new iframe
				var page = document.getElementById(pageid);
				var iframe = document.createElement("iframe");

				// this should match the classes in the noscript tag
				iframe.className = "preload " + pageid;

				if(page.checked)
					// immediately load the page we're displaying first
					iframe.src = src;
				else
					// otherwise delay until someone navigates to this page
					page.addEventListener("change", function() {
						iframe.src = src;
					}, { once: true });

				iframes.appendChild(iframe);
			}</xsl:text>
			<xsl:apply-templates select="//atom:entry" mode="js" />
			<xsl:text>

			// finally, replace the noscript tag with the new iframes
			document.getElementById("content").replaceChild(iframes, document.getElementById("preloadContent"));
		})();
	</xsl:text></script>
</body>
</html>
</xsl:template>

<xsl:template match="*" mode="style">
		#page<xsl:value-of select="position()"/>:checked ~ * .page<xsl:value-of select="position()"/> {
			display: block;
		}
		#page<xsl:value-of select="position()"/>:checked ~ #left label[for="page<xsl:value-of select="position()"/>"] {
			font-weight: bold;
		}<!--
--></xsl:template>

<xsl:template match="*" mode="radio">
	<input type="radio" name="page" id="page{position()}">
		<xsl:if test="position() = 1">
			<xsl:attribute name="checked">checked</xsl:attribute>
		</xsl:if>
	</input>
</xsl:template>

<xsl:template match="*" mode="top">
	<label class="preload page{position()} before">
		<xsl:if test="position() &gt; 1">
			<xsl:attribute name="for">page<xsl:value-of select="position() - 1"/></xsl:attribute>
		</xsl:if>
	</label>
	<div class="preload page{position()} title">
		<xsl:value-of select="atom:title"/>
		<time datetime="{atom:published}">
			<xsl:value-of select="substring-before(atom:published, 'T')"/>
		</time>
	</div>
	<label class="preload page{position()} after">
		<xsl:if test="position() &lt; last()">
			<xsl:attribute name="for">page<xsl:value-of select="position() + 1"/></xsl:attribute>
		</xsl:if>
	</label>
</xsl:template>

<xsl:template match="*" mode="iframe">
	<iframe class="preload page{position()}" src="{atom:link[@rel='alternate']/@href}"/>
</xsl:template>

<xsl:template match="*" mode="left">
	<li>
		<label for="page{position()}">
			<xsl:value-of select="atom:title"/>
			<time datetime="{atom:published}">
				<xsl:value-of select="substring-before(atom:published, 'T')"/>
			</time>
		</label>
	</li>
</xsl:template>

<xsl:template match="*" mode="js">
			preload("page<xsl:value-of select="position()"/>", "<xsl:value-of select="atom:link[@rel='alternate']/@href"/>");<!--
--></xsl:template>

</xsl:stylesheet>
