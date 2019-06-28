<?xml version="1.0"?>

<xsl:stylesheet
    version="1.0"
    exclude-result-prefixes="atom"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:output method="html" omit-xml-declaration="yes" indent="no"/>

<xsl:param name="iconprev"/>
<xsl:param name="iconnext"/>

<xsl:template match="/">
<html>
<head>
	<meta name="generator" content="https://github.com/jameysharp/reader-py" />
	<meta name="viewport" content="width=device-width" />
	<title><xsl:value-of select="//atom:feed/atom:title"/></title>
	<style>
		body {
			position: absolute;
			width: 100%;
			height: 100%;
			margin: 0;
			display: flex;
			flex-direction: column-reverse;
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
		#top a.preload {
			background-color: #4A1600;
			background-position: center;
			background-repeat: no-repeat;
			width: 2.2em;
			height: 2.2em;
		}
		#top a.preload[href] {
			background-color: #93320C;
		}
		#top a.preload[href]:hover {
			background-color: #4A1600;
		}
		a.before {
			background-image: url('<xsl:value-of select="$iconprev"/>');
		}
		a.after {
			background-image: url('<xsl:value-of select="$iconnext"/>');
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
		#left a {
			text-decoration: none;
			color: black;
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
		iframe {
			flex-grow: 1;
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
	<script>
		document.body.addEventListener("click", function(e) {
			var target = e.target;
			while(target != null) {
				if(target.nodeName == "A") {
					window.frames[0].frameElement.src = target.href;
					e.preventDefault();
					return;
				}
				target = target.parentElement;
			}
		}, true);
	</script>

	<input type="checkbox" id="expand-sidebar" />

	<iframe name="content" src="{//atom:entry[1]/atom:link[@rel='alternate']/@href}"/>

	<div id="top">
		<label for="expand-sidebar" id="expand-sidebar-btn">&#187;</label>
		<xsl:apply-templates select="//atom:entry" mode="top" />
	</div>

	<div id="left">
		<ul>
		<xsl:apply-templates select="//atom:entry" mode="left" />
		</ul>
	</div>
</body>
</html>
</xsl:template>

<xsl:template match="*" mode="style">
		iframe[src="<xsl:value-of select="atom:link[@rel='alternate']/@href"/>"] ~ * .page<xsl:value-of select="position()"/> {
			display: block;
		}
		iframe[src="<xsl:value-of select="atom:link[@rel='alternate']/@href"/>"] ~ #left a[href="<xsl:value-of select="atom:link[@rel='alternate']/@href"/>"] {
			font-weight: bold;
		}<!--
--></xsl:template>

<xsl:template match="*" mode="top">
	<a class="preload page{position()} before">
		<xsl:if test="position() &gt; 1">
			<xsl:attribute name="href"><xsl:value-of select="preceding-sibling::*[1]/atom:link[@rel='alternate']/@href"/></xsl:attribute>
			<xsl:attribute name="target">content</xsl:attribute>
		</xsl:if>
	</a>
	<div class="preload page{position()} title">
		<xsl:value-of select="atom:title"/>
		<time datetime="{atom:published}">
			<xsl:value-of select="substring-before(atom:published, 'T')"/>
		</time>
	</div>
	<a class="preload page{position()} after">
		<xsl:if test="position() &lt; last()">
			<xsl:attribute name="href"><xsl:value-of select="following-sibling::*[1]/atom:link[@rel='alternate']/@href"/></xsl:attribute>
			<xsl:attribute name="target">content</xsl:attribute>
		</xsl:if>
	</a>
</xsl:template>

<xsl:template match="*" mode="left">
	<li>
		<a href="{atom:link[@rel='alternate']/@href}" target="content">
			<xsl:value-of select="atom:title"/>
			<time datetime="{atom:published}">
				<xsl:value-of select="substring-before(atom:published, 'T')"/>
			</time>
		</a>
	</li>
</xsl:template>

</xsl:stylesheet>
